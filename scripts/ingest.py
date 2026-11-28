"""Queue an ingestion through your API and watch the worker do it.

Usage:
  uv run python scripts/ingest.py --limit 20
  uv run python scripts/ingest.py --limit 20 --url https://your-app.onrender.com
  uv run python scripts/ingest.py --retry-failed
  uv run python scripts/ingest.py --watch JOB_ID

On a public URL, configure ADMIN_TOKEN in your local .env
and in your Render environment variables.
"""

import argparse
import sys
import time

import httpx

from nutrinin.config import get_settings


def parse_response(response: httpx.Response):
    """Parse JSON safely and display useful information on failure."""
    try:
        return response.json()
    except ValueError:
        print("\nAPI returned a non-JSON response.")
        print("HTTP STATUS:", response.status_code)
        print("CONTENT TYPE:", response.headers.get("content-type", "unknown"))
        print("RESPONSE:", response.text[:1000])
        return None


def show(progress: dict) -> str:
    """Format ingestion progress safely."""
    counts = progress.get("counts", {})
    parts = " ".join(f"{name}={value}" for name, value in counts.items())

    pages = progress.get("pages", 0)
    seconds = progress.get("seconds", 0)

    return f"{progress.get('status', 'unknown'):<9} {parts} pages={pages} {seconds:.0f}s"


def watch(client: httpx.Client, job_id: str, every: float) -> int:
    """Watch an existing ingestion job until completion."""
    last = ""

    while True:
        try:
            response = client.get(f"/v1/ingest/{job_id}")
        except httpx.TransportError as exc:
            print(f"Connection error while checking job: {exc}")
            return 1

        if response.status_code != 200:
            print(f"HTTP {response.status_code}: {response.text[:1000]}")
            return 1

        progress = parse_response(response)

        if progress is None:
            return 1

        line = show(progress)

        if line.rsplit(" ", 1)[0] != last:
            print(line, flush=True)
            last = line.rsplit(" ", 1)[0]

        if progress.get("status") == "finished":
            break

        time.sleep(every)

    for item in progress.get("dead_letter", []):
        attempts = item.get("attempts", 0)
        tries = "1 try" if attempts == 1 else f"{attempts} tries"

        location = item.get("path") or item.get("url") or "Unknown document"
        error = item.get("error") or "Unknown error"

        print(f"FAILED   {location} ({tries}) {error}")

    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of documents to queue",
    )

    parser.add_argument(
        "--source",
        default="",
        help="Only process this source from the manifest",
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry failed documents",
    )

    parser.add_argument(
        "--watch",
        metavar="JOB_ID",
        help="Watch an existing job without starting ingestion",
    )

    parser.add_argument(
        "--every",
        type=float,
        default=3.0,
        help="Seconds between progress checks",
    )

    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")

    if args.every <= 0:
        parser.error("--every must be greater than 0")

    try:
        settings = get_settings()
        token = settings.admin_token or ""

        headers = {"X-Admin-Token": token}

        with httpx.Client(
            base_url=args.url.rstrip("/"),
            headers=headers,
            timeout=90,
        ) as client:
            # Watch an existing job without creating a new one.
            if args.watch:
                return watch(client, args.watch, args.every)

            body = {
                "limit": args.limit,
                "source": args.source,
                "retry_failed": args.retry_failed,
            }

            print("Connecting to:", args.url)
            print("Requesting ingestion...")
            print("Limit:", args.limit)

            response = client.post("/v1/ingest", json=body)

            answer = parse_response(response)

            if answer is None:
                return 1

            if response.status_code not in (200, 202):
                print(f"HTTP ERROR: {response.status_code}")
                print("API RESPONSE:", answer)
                return 1

            if not isinstance(answer, dict):
                print("Unexpected API response format:", answer)
                return 1

            job_id = answer.get("job_id")

            if not job_id:
                print(
                    answer.get(
                        "detail",
                        "No ingestion job was created.",
                    )
                )
                return 0

            queued = answer.get("queued", 0)

            print(f"HTTP {response.status_code}: job {job_id}, {queued} queued")

            return watch(client, job_id, args.every)

    except httpx.TimeoutException as exc:
        print("API request timed out:", exc)
        return 1

    except httpx.TransportError as exc:
        print(f"{type(exc).__name__}: Cannot connect to API at {args.url}")
        return 1

    except Exception as exc:
        print(f"Unexpected error: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
