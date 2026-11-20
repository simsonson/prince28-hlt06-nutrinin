"""Smoke test a deployed app: is the new version live, alive and ready?

    uv run python scripts/smoke.py https://your-app.onrender.com --expect-version <sha>

Exit code 0 = passed, 1 = failed. Standard library only, so it runs anywhere.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "NutriNIN-smoke-test"})

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read() or b"null")

    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read() or b"null")
        except ValueError:
            return error.code, None

    except (OSError, ValueError) as error:
        return None, str(error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--expect-version")
    parser.add_argument("--timeout", type=int, default=600)

    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    deadline = time.monotonic() + args.timeout

    # 1. Check application health and version
    while time.monotonic() < deadline:
        status, body = get(f"{base}/health")

        version = body.get("version") if isinstance(body, dict) else None

        if status == 200 and (args.expect_version is None or version == args.expect_version):
            print(f"OK /health -> {status}, version {version}")
            break

        print(f"Waiting for deployment: {status} {version}")
        time.sleep(10)
    else:
        print("FAIL: Expected version not available")
        return 1

    # 2. Check database readiness
    status, body = get(f"{base}/ready")

    if status != 200:
        print(f"FAIL /ready -> {status} {body}")
        return 1

    print("OK /ready")

    # 3. Check actual database-backed endpoint
    status, body = get(f"{base}/v1/documents?limit=1")

    if status != 200 or not isinstance(body, dict) or "items" not in body:
        print(f"FAIL documents endpoint -> {status} {body}")
        return 1

    print("OK /v1/documents")
    print("Smoke test passed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
