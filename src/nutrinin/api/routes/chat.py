"""POST /v1/chat (streaming) and GET /v1/usage (what the model calls cost)."""

import json
from collections.abc import AsyncIterator
from dataclasses import asdict, replace
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from nutrinin.api.deps import GatewayDep, UsageDep
from nutrinin.llm.classify import classify
from nutrinin.llm.gateway import LLMResult, LLMUnavailable

router = APIRouter(tags=["chat"])

PROMPT_VERSION = "chat_system_v1"  # the file prompts/chat_system_v1.md
ROUTER_PROMPT_VERSION = "classify_v2"  # best measured accuracy/token trade-off
ROUTE_REPLIES = {
    "personal": "I can't know that from my documents.",
    "off_topic": "That question is outside NutriNIN's subject.",
    "invalid": "I can't tell whether my documents can answer that question.",
}


def load_prompt(directory: Path, name: str = PROMPT_VERSION) -> str:
    """Read a prompt file. A missing file stops the app at start-up: fail fast."""
    return (directory / f"{name}.md").read_text(encoding="utf-8").strip()


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    stream: bool = True
    history: list[HistoryMessage] = Field(default_factory=list, max_length=6)


def sse(data: dict, event: str = "") -> str:
    """One server-sent event: an optional name, a JSON payload, and a blank line."""
    head = f"event: {event}\n" if event else ""
    return f"{head}data: {json.dumps(data, ensure_ascii=False)}\n\n"


def summary(result: LLMResult) -> dict:
    return {k: v for k, v in asdict(result).items() if k != "text"}


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, gateway: GatewayDep):
    try:
        label, router_result = await classify(
            gateway,
            request.app.state.router_prompt,
            ROUTER_PROMPT_VERSION,
            body.message,
        )
    except LLMUnavailable as exc:
        raise HTTPException(
            status_code=503, detail=f"No model could classify the question: {exc}"
        ) from exc

    if label != "docs":
        answer = ROUTE_REPLIES[label]
        result = replace(router_result, text=answer)
        if not body.stream:
            return {"answer": answer, **summary(result), "classification": label}

        async def fixed_events() -> AsyncIterator[str]:
            yield sse({"delta": answer})
            yield sse({**summary(result), "classification": label}, event="done")

        headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        return StreamingResponse(fixed_events(), media_type="text/event-stream", headers=headers)

    messages = [
        {"role": "system", "content": request.app.state.system_prompt},
        *[item.model_dump() for item in body.history],
        {"role": "user", "content": body.message},
    ]
    try:
        if not body.stream:
            result = await gateway.generate(messages, prompt_version=PROMPT_VERSION)
            return {
                "answer": result.text,
                **summary(result),
                "classification": label,
                "classifier": summary(router_result),
            }
        stream = gateway.stream(messages, prompt_version=PROMPT_VERSION)
        first = await anext(stream)  # wait for the first piece BEFORE sending status 200
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"No model could answer: {exc}") from exc

    async def events() -> AsyncIterator[str]:
        item: str | LLMResult = first
        try:
            while True:
                if isinstance(item, LLMResult):
                    yield sse(
                        {
                            **summary(item),
                            "classification": label,
                            "classifier": summary(router_result),
                        },
                        event="done",
                    )
                    return
                yield sse({"delta": item})
                item = await anext(stream)
        except LLMUnavailable as exc:  # the status line is long gone: say it in the stream
            yield sse({"detail": str(exc)}, event="error")

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(events(), media_type="text/event-stream", headers=headers)


@router.get("/llm/status")
async def llm_status(gateway: GatewayDep) -> dict:
    """Report configured providers and their current circuit-breaker states."""
    return {
        "providers": [
            {
                "name": provider.name,
                "model": provider.model,
                "state": gateway.breakers[provider.name].state,
            }
            for provider in gateway.providers
        ]
    }


@router.get("/usage")
async def usage(repo: UsageDep, days: Annotated[int, Query(ge=1, le=90)] = 7) -> dict:
    """Tokens and rupees per day, from the llm_calls table."""
    rows = await repo.by_day(days)
    total = round(sum(row["cost_inr"] for row in rows), 4)
    return {"days": rows, "total_cost_inr": total, "calls": sum(row["calls"] for row in rows)}
