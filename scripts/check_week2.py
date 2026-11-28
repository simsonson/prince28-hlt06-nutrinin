"""Week 2 self-check: the same things the nightly scan looks at, run on your laptop.

    uv run python scripts/check_week2.py                     # files, git, tests
    uv run python scripts/check_week2.py https://x.onrender.com   # + the live URL

Standard library only. It never changes anything; it only reads and reports.
(The live part asks your product one short question: that is one model call.)
"""

import contextlib
import json
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path.cwd()
OK, BAD, WARN = "  ok ", "  ✗  ", "  !  "
LABELS = {"docs", "personal", "off_topic"}
KEY_SHAPES = r"AIza[0-9A-Za-z_-]{35}|gsk_[0-9A-Za-z]{30,}"  # what real model keys look like
results: list[tuple[str, bool]] = []


def check(day: str, label: str, passed: bool, hint: str = "", warn_only: bool = False) -> None:
    mark = OK if passed else (WARN if warn_only else BAD)
    print(f"{mark}{label}" + ("" if passed or not hint else f"\n       → {hint}"))
    if not warn_only:
        results.append((day, passed))


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace") if exists(path) else ""


def call(url: str, body: dict | None = None, timeout: int = 90) -> tuple[int, object]:
    """GET, or POST when a body is given. Returns (status, parsed JSON or None)."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read() or b"null")
        except ValueError:
            return error.code, None


def main() -> int:
    live = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
    if not exists("pyproject.toml"):
        print("Run this from your project folder (where pyproject.toml is).")
        return 2
    pyproject = tomllib.loads(text("pyproject.toml"))
    pkg = pyproject["project"]["name"].replace("-", "_")
    deps = " ".join(pyproject["project"].get("dependencies", [])).lower()
    readme, notes = text("README.md"), text("NOTES.md")
    tracked = run(["git", "ls-files"]).stdout.split("\n")
    migrations = " ".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in (ROOT / "migrations/versions").glob("*.py")
    )

    print("\nD06 · collecting your corpus  (D06 Build Lab)")
    for f in [f"src/{pkg}/ingest/fetch.py", "scripts/fetch.py", "DATASET.md", "docs/CAPACITY.md"]:
        check("D06", f, exists(f), "missing: see the D06 Build Lab")
    downloaded = 0
    for line in text("data/manifest.jsonl").splitlines():
        with contextlib.suppress(ValueError):
            downloaded += json.loads(line).get("status") == "downloaded"
    check(
        "D06",
        f"data/manifest.jsonl lists downloaded files ({downloaded} found)",
        downloaded > 0,
        "run scripts/fetch.py and commit data/manifest.jsonl",
    )
    raw = [p for p in tracked if p.startswith("data/raw/")]
    check("D06", "data/raw/ is NOT committed", not raw, "git rm -r --cached data/raw")

    print("\nD07 · parsing  (D07 Build Lab)")
    for f in [
        f"src/{pkg}/ingest/parse.py",
        f"src/{pkg}/ingest/store.py",
        "scripts/parse_corpus.py",
    ]:
        check("D07", f, exists(f), "missing: see the D07 Build Lab")
    check(
        "D07",
        "a migration creates parse_failures",
        "parse_failures" in migrations,
        'uv run alembic revision --autogenerate -m "add page headings and parse_failures"',
    )
    pinned = re.search(r"pymupdf[^ ]*<2", deps) is not None
    check("D07", "pymupdf is pinned below version 2", pinned, 'uv add "pymupdf>=1.26,<2"')
    check(
        "D07",
        "NOTES.md has the parser comparison table",
        "<!-- parsers:start -->" in notes,
        "uv run python scripts/compare_parsers.py",
    )

    print("\nD08 · LLM gateway  (D08 Build Lab)")
    for f in [f"src/{pkg}/llm/gateway.py", f"src/{pkg}/api/routes/chat.py"]:
        check("D08", f, exists(f), "missing: see the D08 Build Lab")
    prompt = text("prompts/chat_system_v1.md")
    check(
        "D08",
        'prompts/chat_system_v1.md allows "I am not sure"',
        "not sure" in prompt,
        "the file is missing, or the line was removed",
    )
    check("D08", "a migration creates llm_calls", "llm_calls" in migrations, "D08 Milestone 2")
    env_example = text(".env.example")
    names_only = all(
        re.search(rf"^{name}=[ \t]*$", env_example, flags=re.M)
        for name in ("GEMINI_API_KEY", "GROQ_API_KEY")
    )
    check(
        "D08",
        ".env.example names both keys, with empty values",
        names_only,
        "GEMINI_API_KEY= and GROQ_API_KEY= with nothing after the = sign",
    )
    leaked = run(["git", "grep", "-I", "-l", "-E", KEY_SHAPES]).stdout.split()
    check(
        "D08",
        "no model key in any committed file",
        ".env" not in tracked and not leaked,
        f"found in {leaked or ['.env']}: remove it, then create NEW keys (the old ones are public)",
    )
    check(
        "D08",
        "the Dockerfile copies prompts/",
        "prompts ./prompts" in text("Dockerfile"),
        "COPY --chown=app:app prompts ./prompts",
    )

    print("\nD09 · prompts and structured output  (D09 Build Lab)")
    versions = sorted(p.name for p in (ROOT / "prompts").glob("classify_v*.md"))
    check(
        "D09",
        f"3+ router prompts in prompts/ ({len(versions)} found)",
        len(versions) >= 3,
        "classify_v1.md, classify_v2.md, classify_v3.md",
    )
    unfinished = [name for name in versions if "TODO" in text(f"prompts/{name}")]
    check(
        "D09",
        "no TODO left in the router prompts",
        not unfinished,
        f"write your own examples in {unfinished}",
        warn_only=True,
    )
    rows, todo = [], 0
    for line in text("eval/prompt_testset.jsonl").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("label") in LABELS and row.get("question"):
            rows.append(row)
            todo += "TODO" in row["question"]
    check(
        "D09",
        f"eval/prompt_testset.jsonl has 20 labelled questions ({len(rows) - todo} ready)",
        len(rows) - todo >= 20,
        f"{todo} lines still say TODO" if todo else "one JSON object per line, three labels",
    )
    for f in [f"src/{pkg}/llm/extract.py", f"src/{pkg}/llm/doc_meta.py"]:
        check("D09", f, exists(f), "missing: see the D09 Build Lab")
    check(
        "D09",
        "an extract prompt exists (prompts/extract_v*.md)",
        any((ROOT / "prompts").glob("extract_v*.md")),
        "D09 Milestone 4",
    )
    check(
        "D09",
        "NOTES.md has the prompt comparison table",
        "<!-- prompts:start -->" in notes,
        "uv run python scripts/compare_prompts.py",
    )

    print("\nD10 · queue and worker  (D10 Build Lab)")
    for f in [f"src/{pkg}/workers/ingest.py", f"src/{pkg}/api/routes/ingest.py"]:
        check("D10", f, exists(f), "missing: see the D10 Build Lab")
    check(
        "D10", "a migration creates ingest_items", "ingest_items" in migrations, "D10 Milestone 1"
    )
    check(
        "D10",
        "docker-compose.yml has a worker service",
        re.search(r"^  worker:", text("docker-compose.yml"), flags=re.M) is not None,
        "D10 Milestone 6",
    )
    report = text("docs/INGEST_REPORT.md")
    check(
        "D10",
        "docs/INGEST_REPORT.md is generated and committed",
        "<!-- generated:start -->" in report and "docs/INGEST_REPORT.md" in tracked,
        "uv run python scripts/ingest_report.py, then commit it",
    )
    tags = run(["git", "tag", "--list", "week-2"]).stdout.strip()
    check("D10", "tag week-2 exists", tags == "week-2", "git tag -a week-2 -m … on main, then push")

    print("\nTests")
    tests = run(["uv", "run", "pytest", "tests/unit"])
    found = re.search(r"\d+ (passed|failed|error)[^\n]*", tests.stdout)
    check(
        "TESTS",
        f"unit tests pass ({found.group(0) if found else 'no test summary'})",
        tests.returncode == 0,
        "uv run poe test, and read the FIRST failure",
    )

    url_in_readme = re.search(r"https://[\w.-]+\.onrender\.com", readme)
    if live or url_in_readme:
        base = live or url_in_readme.group(0)
        print(f"\nLive · {base}  (the first request may take a minute if it was asleep)")
        try:
            status, body = call(f"{base}/health")
            version = str(body.get("version"))[:7] if isinstance(body, dict) else "?"
            check("LIVE", f"/health → {status}, version {version}", status == 200, "Render → Logs")
            status, body = call(f"{base}/v1/chat", {"message": "Reply with OK.", "stream": False})
            who = body.get("provider") if isinstance(body, dict) else None
            check(
                "LIVE",
                f"POST /v1/chat → {status}" + (f", answered by {who}" if who else ""),
                status == 200 and bool(who),
                "503: are GEMINI_API_KEY and GROQ_API_KEY set in Render → Environment?",
            )
            status, body = call(f"{base}/v1/usage")
            calls = body.get("calls", 0) if isinstance(body, dict) else 0
            check(
                "LIVE",
                f"/v1/usage → {status}, {calls} model calls this week",
                status == 200 and calls > 0,
                "no rows: is the llm_calls migration applied to Neon?",
            )
            status, _ = call(f"{base}/v1/ingest", {"limit": 1})
            hint = {
                202: "DANGER: anyone can start an ingestion. Set ADMIN_TOKEN in Render",
                200: "DANGER: anyone can start an ingestion. Set ADMIN_TOKEN in Render",
                403: "set ADMIN_TOKEN in Render → Environment",
                404: "the ingest router is not deployed: did D10's pull request merge?",
            }.get(status, "Render → Logs")
            check("LIVE", f"POST /v1/ingest without a token → {status}", status == 401, hint)
            status, body = call(f"{base}/v1/ingest/dead-letter")
            count = body.get("count") if isinstance(body, dict) else "?"
            check(
                "LIVE", f"/v1/ingest/dead-letter → {status} ({count} items)", status == 200, "D10"
            )
        except Exception as error:  # noqa: BLE001 - any failure means "not live"
            check("LIVE", "the live URL answers", False, f"{error}: open Render → Logs")

    total, passed = len(results), sum(ok for _, ok in results)
    print(f"\n{passed} of {total} checks passed.")
    for day in ["D06", "D07", "D08", "D09", "D10", "TESTS", "LIVE"]:
        missing = [ok for d, ok in results if d == day and not ok]
        if missing:
            print(f"Start with {day}: it has {len(missing)} open item(s). Later days build on it.")
            break
    else:
        print("Week 2 is complete. 🚀")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
