"""Send quick readiness requests so the API logs its post-request pool status."""

import argparse
import asyncio
from collections import Counter

import httpx


async def main(base_url: str, requests: int) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=5) as client:
        statuses = []
        for _ in range(requests):
            response = await client.get("/ready")
            statuses.append(response.status_code)
    print(f"sent={len(statuses)} status_codes={dict(Counter(statuses))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.requests))
