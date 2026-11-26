"""/v1/chat and /v1/usage, with the fake model from tests/conftest.py."""

import json

from nutrinin.api.deps import get_gateway
from nutrinin.llm.gateway import FakeLLM, LLMError, LLMGateway


def events(body: str) -> list[tuple[str, dict]]:
    """Parse a server-sent-event body into (event name, data) pairs."""
    out = []
    for block in body.strip().split("\n\n"):
        name = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                out.append((name, json.loads(line[5:])))
    return out


def test_chat_without_streaming_returns_json(client, llm):
    llm.script = ["docs", "Use curly braces in the path."]
    r = client.post(
        "/v1/chat", json={"message": "How do I declare a path parameter?", "stream": False}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Use curly braces in the path."
    assert body["provider"] == "fake" and body["tokens_out"] == 6 and "cost_inr" in body
    assert body["classification"] == "docs" and llm.calls == 2


def test_personal_question_gets_fixed_unknown_without_a_second_model_call(client, llm):
    llm.script = ["personal"]
    r = client.post(
        "/v1/chat",
        json={
            "message": "What will vegetable prices be at Koyambedu market tomorrow?",
            "stream": False,
        },
    )
    assert r.status_code == 200
    assert r.json()["answer"] == "I can't know that from my documents."
    assert r.json()["classification"] == "personal" and llm.calls == 1


def test_off_topic_question_gets_fixed_decline_without_a_second_model_call(client, llm):
    llm.script = ["off_topic"]
    r = client.post(
        "/v1/chat", json={"message": "How do I fix a flat bicycle tyre?", "stream": False}
    )
    assert r.status_code == 200
    assert r.json()["answer"] == "That question is outside NutriNIN's subject."
    assert r.json()["classification"] == "off_topic" and llm.calls == 1


def test_chat_includes_bounded_history_between_system_and_current_message(client, llm):
    llm.script = ["docs", "An adult's needs depend on body weight."]
    r = client.post(
        "/v1/chat",
        json={
            "message": "And for children?",
            "stream": False,
            "history": [
                {"role": "user", "content": "How much protein do adults need?"},
                {"role": "assistant", "content": "It depends on age and activity."},
            ],
        },
    )
    assert r.status_code == 200
    messages = llm.seen[-1]["messages"]
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1]["content"] == "And for children?"


def test_chat_rejects_more_than_six_history_messages(client):
    history = [{"role": "user", "content": "Earlier question."}] * 7
    r = client.post("/v1/chat", json={"message": "Follow up", "history": history})
    assert r.status_code == 422


def test_llm_status_lists_fake_provider_and_closed_breaker(client, llm):
    r = client.get("/v1/llm/status")
    assert r.status_code == 200
    assert r.json() == {"providers": [{"name": "fake", "model": "fake-1", "state": "closed"}]}


def test_llm_status_watches_closed_open_half_open_and_recovery(client):
    now = [0.0]
    primary = FakeLLM(
        "primary",
        "primary-model",
        [LLMError("offline", retryable=False) for _ in range(3)] + ["docs", "Back."],
    )
    backup = FakeLLM("backup", "backup-model", ["docs", "Fallback answer."] * 3)
    gateway = LLMGateway(
        [primary, backup],
        max_attempts=1,
        breaker_cooldown=30,
        clock=lambda: now[0],
    )
    client.app.dependency_overrides[get_gateway] = lambda: gateway

    assert [p["state"] for p in client.get("/v1/llm/status").json()["providers"]] == [
        "closed",
        "closed",
    ]
    for attempt in range(3):
        answer = client.post(
            "/v1/chat", json={"message": f"Trigger primary failure {attempt + 1}", "stream": False}
        )
        assert answer.status_code == 200 and answer.json()["provider"] == "backup"
        expected_primary_state = "closed" if attempt == 0 else "open"
        assert (
            client.get("/v1/llm/status").json()["providers"][0]["state"] == expected_primary_state
        )
    assert [p["state"] for p in client.get("/v1/llm/status").json()["providers"]] == [
        "open",
        "closed",
    ]

    now[0] = 30.0
    assert [p["state"] for p in client.get("/v1/llm/status").json()["providers"]] == [
        "half-open",
        "closed",
    ]
    answer = client.post("/v1/chat", json={"message": "Try primary again", "stream": False})
    assert answer.status_code == 200 and answer.json()["provider"] == "primary"
    assert [p["state"] for p in client.get("/v1/llm/status").json()["providers"]] == [
        "closed",
        "closed",
    ]


def test_chat_streams_pieces_and_ends_with_a_done_event(client, llm):
    llm.script = ["docs", "Use curly braces in the path."]
    r = client.post("/v1/chat", json={"message": "How do I declare a path parameter?"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    received = events(r.text)
    text = "".join(data["delta"] for name, data in received if name == "")
    assert text.strip() == "Use curly braces in the path."
    assert received[-1][0] == "done" and received[-1][1]["model"] == "fake-1"


def test_the_model_gets_the_system_prompt_from_the_prompt_file(client):
    assert "not sure" in client.app.state.system_prompt


def test_an_empty_message_is_a_422_problem(client):
    r = client.post("/v1/chat", json={"message": ""})
    assert r.status_code == 422 and r.headers["content-type"] == "application/problem+json"


def test_when_no_model_can_answer_the_api_says_503_not_200(client, llm):
    llm.script = ["docs", LLMError("HTTP 401: invalid API key", retryable=False)]
    r = client.post("/v1/chat", json={"message": "hello"})
    assert r.status_code == 503 and "No model could answer" in r.json()["detail"]


def test_a_failure_in_the_middle_of_a_stream_is_reported_as_an_error_event(client, llm):
    llm.script = ["docs", ("partial", LLMError("HTTP 503: overloaded", retryable=True))]
    r = client.post("/v1/chat", json={"message": "hello"})
    assert r.status_code == 200  # too late to change it: the first bytes were already sent
    assert events(r.text)[-1][0] == "error"


def test_usage_reports_tokens_and_rupees_per_day(client):
    r = client.get("/v1/usage")
    assert r.status_code == 200
    body = r.json()
    assert body["days"][0]["tokens_in"] == 300 and body["total_cost_inr"] == 0.0642
    assert body["calls"] == 3
