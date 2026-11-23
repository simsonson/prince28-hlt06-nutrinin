"""The downloader, tested without the internet: httpx.MockTransport plays the website."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from nutrinin.ingest import fetch
from nutrinin.ingest.fetch import Source, fetch_all

SITE = "https://docs.example.org"


def make_sources(count: int) -> list[Source]:
    licence = "CC BY 4.0"
    return [
        Source(
            f"{SITE}/guide/page-{i}.html",
            "Example Docs",
            licence,
            permission_status="approved",
        )
        for i in range(count)
    ]


class FakeSite:
    """A tiny website. `plan` lists status codes a path answers with before 200."""

    def __init__(
        self,
        robots: str | int = 404,
        plan: dict[str, list[int]] | None = None,
        etag: str | None = None,
    ) -> None:
        self.robots = robots
        self.plan = plan or {}
        self.etag = etag
        self.error_headers: dict[str, str] = {}
        self.request_headers: list[httpx.Headers] = []
        self.hits: list[str] = []
        self.busy = 0
        self.max_busy = 0
        self.slept: list[float] = []

    async def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path == "/robots.txt":
            if isinstance(self.robots, int):
                return httpx.Response(self.robots)
            return httpx.Response(200, text=self.robots)

        self.hits.append(path)
        self.request_headers.append(request.headers)
        if self.etag and request.headers.get("If-None-Match") == self.etag:
            return httpx.Response(304, headers={"ETag": self.etag})
        self.busy += 1
        self.max_busy = max(self.max_busy, self.busy)

        await asyncio.sleep(0.005)
        self.busy -= 1

        queue = self.plan.get(path)
        status = queue.pop(0) if queue else 200

        if status != 200:
            return httpx.Response(status, headers=self.error_headers)

        headers = {"ETag": self.etag} if self.etag else None
        return httpx.Response(200, html=f"<h1>{path}</h1>", headers=headers)

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)

    async def run(
        self,
        sources: list[Source],
        root: Path,
        **options,
    ) -> dict[str, int]:
        transport = httpx.MockTransport(self.handler)

        async with httpx.AsyncClient(
            transport=transport,
            follow_redirects=True,
        ) as client:
            return await fetch_all(
                sources,
                root=root,
                client=client,
                sleep=self.sleep,
                per_host_delay=0,
                **options,
            )


def manifest(root: Path) -> list[dict]:
    lines = (root / "data" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()

    return [json.loads(line) for line in lines]


def raw_files(root: Path) -> list[Path]:
    return [path for path in (root / "data" / "raw").rglob("*") if path.is_file()]


# ---------- successful downloads ----------


async def test_downloads_files_and_records_where_they_came_from(tmp_path):
    counts = await FakeSite().run(make_sources(3), tmp_path)

    assert counts == {
        "downloaded": 3,
        "skipped": 0,
        "blocked": 0,
        "failed": 0,
    }

    record = manifest(tmp_path)[0]

    assert record["status"] == "downloaded"
    assert record["licence"] == "CC BY 4.0"
    assert record["permission_status"] == "approved"

    saved = tmp_path / record["path"]

    assert saved.parent == tmp_path / "data" / "raw" / "example-docs"
    assert saved.suffix == ".html"
    assert saved.stat().st_size == record["bytes"]
    assert len(record["sha256"]) == 64


async def test_second_run_downloads_nothing(tmp_path):
    site = FakeSite()

    await site.run(make_sources(5), tmp_path)
    counts = await site.run(make_sources(5), tmp_path)

    assert counts["skipped"] == 5
    assert counts["downloaded"] == 0
    assert len(site.hits) == 5


async def test_refresh_sends_etag_and_records_not_modified(tmp_path):
    site = FakeSite(etag='"v1"')
    sources = make_sources(1)

    await site.run(sources, tmp_path)
    counts = await site.run(sources, tmp_path, refresh=True)

    assert counts == {"downloaded": 0, "skipped": 1, "blocked": 0, "failed": 0}
    assert site.request_headers[-1].get("If-None-Match") == '"v1"'
    record = manifest(tmp_path)[-1]
    assert record["status"] == "not_modified"
    assert record["etag"] == '"v1"'
    assert len(raw_files(tmp_path)) == 1


async def test_refresh_block_does_not_replace_existing_download(tmp_path):
    sources = make_sources(1)
    await FakeSite().run(sources, tmp_path)

    blocked = FakeSite(robots="User-agent: *\nDisallow: /\n")
    counts = await blocked.run(sources, tmp_path, refresh=True)

    assert counts["blocked"] == 1
    assert await FakeSite().run(sources, tmp_path) == {
        "downloaded": 0,
        "skipped": 1,
        "blocked": 0,
        "failed": 0,
    }


async def test_resume_fetches_only_what_is_missing(tmp_path):
    site = FakeSite()

    await site.run(make_sources(3), tmp_path)
    counts = await site.run(make_sources(8), tmp_path)

    assert counts == {
        "downloaded": 5,
        "skipped": 3,
        "blocked": 0,
        "failed": 0,
    }

    assert len(site.hits) == 8
    assert len(set(site.hits)) == 8


async def test_deleted_file_is_downloaded_again(tmp_path):
    site = FakeSite()

    await site.run(make_sources(2), tmp_path)
    raw_files(tmp_path)[0].unlink()

    counts = await site.run(make_sources(2), tmp_path)

    assert counts["downloaded"] == 1
    assert counts["skipped"] == 1


# ---------- retry behaviour ----------


async def test_retries_a_503_and_then_succeeds(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [503, 503]})

    counts = await site.run(make_sources(1), tmp_path)

    assert counts["downloaded"] == 1
    assert manifest(tmp_path)[0]["attempts"] == 3
    assert len(site.slept) == 2


async def test_obeys_retry_after_on_429(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [429]})
    site.error_headers = {"Retry-After": "7"}

    counts = await site.run(make_sources(1), tmp_path)

    assert counts["downloaded"] == 1
    assert site.slept
    assert site.slept[0] >= 7


async def test_gives_up_after_max_attempts_and_leaves_no_file(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [500] * 10})

    counts = await site.run(
        make_sources(1),
        tmp_path,
        max_attempts=3,
    )

    assert counts["failed"] == 1
    assert len(site.hits) == 3

    record = manifest(tmp_path)[0]

    assert record["status"] == "failed"
    assert record["http_status"] == 500
    assert raw_files(tmp_path) == []


async def test_404_is_not_retried(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [404]})

    counts = await site.run(make_sources(1), tmp_path)

    assert counts["failed"] == 1
    assert len(site.hits) == 1
    assert site.slept == []


async def test_a_failed_file_is_tried_again_on_the_next_run(tmp_path):
    site = FakeSite(plan={"/guide/page-0.html": [404]})

    await site.run(make_sources(1), tmp_path)
    counts = await site.run(make_sources(1), tmp_path)

    assert counts["downloaded"] == 1


# ---------- robots.txt behaviour ----------


async def test_robots_disallow_means_never_requested(tmp_path):
    site = FakeSite(robots="User-agent: *\nDisallow: /guide/\n")

    counts = await site.run(make_sources(3), tmp_path)

    assert counts["blocked"] == 3
    assert site.hits == []


async def test_robots_longest_match_wins(tmp_path):
    site = FakeSite(robots=("User-agent: *\nDisallow: /guide/\nAllow: /guide/page-1\n"))

    counts = await site.run(make_sources(3), tmp_path)

    assert counts["blocked"] == 2
    assert site.hits == ["/guide/page-1.html"]


async def test_robots_server_error_blocks_the_whole_site(tmp_path):
    counts = await FakeSite(robots=503).run(
        make_sources(2),
        tmp_path,
    )

    assert counts["blocked"] == 2


# ---------- concurrency ----------


async def test_never_more_than_max_concurrency_at_once(tmp_path):
    site = FakeSite()

    await site.run(
        make_sources(20),
        tmp_path,
        max_concurrency=4,
    )

    assert 1 < site.max_busy <= 4


# ---------- interrupted download ----------


async def test_broken_connection_leaves_no_half_file(tmp_path):
    async def body():
        yield b"<h1>first half"
        raise httpx.ReadError("connection lost")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)

        return httpx.Response(
            200,
            content=body(),
            headers={"Content-Type": "text/html"},
        )

    async def no_sleep(seconds: float) -> None:
        return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        counts = await fetch_all(
            make_sources(1),
            root=tmp_path,
            client=client,
            sleep=no_sleep,
            max_attempts=2,
        )

    assert counts["failed"] == 1
    assert manifest(tmp_path)[0]["error"] == "ReadError"
    assert raw_files(tmp_path) == []


# ---------- utility functions ----------


def test_backoff_grows_but_stays_inside_its_limits():
    for attempt in range(12):
        ceiling = min(60.0, 2.0**attempt)

        assert all(0 <= fetch.backoff_delay(attempt) <= ceiling for _ in range(50))


def test_retry_after_understands_seconds_and_dates():
    assert fetch.retry_after_seconds("120") == 120.0

    assert fetch.retry_after_seconds("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0

    assert fetch.retry_after_seconds("soon") is None
    assert fetch.retry_after_seconds(None) is None


def test_file_names_are_stable_and_safe():
    url = "https://example.org/files/Annual Report (2024): Final?.PDF"

    stem = fetch.file_stem(url)

    assert stem == fetch.file_stem(url)
    assert stem != fetch.file_stem(url + "x")
    assert all(ch.isalnum() or ch == "-" for ch in stem)

    assert (
        fetch.pick_ext(
            "https://example.org/a/b.PDF",
            "text/html",
        )
        == ".pdf"
    )

    assert (
        fetch.pick_ext(
            "https://example.org/view.aspx?id=7",
            "application/pdf",
        )
        == ".pdf"
    )

    assert (
        fetch.pick_ext(
            "https://example.org/thing",
            "weird/type",
        )
        == ".bin"
    )


# ---------- CSV source registry ----------


def test_read_sources_skips_notes_and_duplicates(tmp_path):
    path = tmp_path / "sources.csv"

    path.write_text(
        "# my notes\n"
        "url,source,licence,title\n"
        "https://example.org/a.pdf,example,CC BY 4.0,Report A\n"
        "\n"
        "https://example.org/a.pdf,example,CC BY 4.0,Report A again\n"
        'https://example.org/b.pdf,example,"Public, cite the page",\n',
        encoding="utf-8",
    )

    sources = fetch.read_sources(path)

    assert [source.url for source in sources] == [
        "https://example.org/a.pdf",
        "https://example.org/b.pdf",
    ]

    assert sources[1].licence == "Public, cite the page"
    assert all(source.permission_status == "unknown" for source in sources)


def test_a_source_without_a_licence_is_refused(tmp_path):
    path = tmp_path / "sources.csv"

    path.write_text(
        "url,source,licence,title\nhttps://example.org/a.pdf,example,,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="licence"):
        fetch.read_sources(path)


def test_read_sources_accepts_approved_permission(tmp_path):
    path = tmp_path / "sources.csv"

    path.write_text(
        "url,source,licence,title,permission_status\n"
        "https://example.org/a.pdf,example,CC BY 4.0,Report A,approved\n",
        encoding="utf-8",
    )

    sources = fetch.read_sources(path)

    assert len(sources) == 1
    assert sources[0].permission_status == "approved"


def test_read_sources_rejects_invalid_permission_status(tmp_path):
    path = tmp_path / "sources.csv"

    path.write_text(
        "url,source,licence,title,permission_status\n"
        "https://example.org/a.pdf,example,CC BY 4.0,Report A,maybe\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="permission_status"):
        fetch.read_sources(path)


# ---------- permission gate ----------


@pytest.mark.parametrize(
    "permission_status",
    ["pending", "denied", "unknown"],
)
async def test_unapproved_sources_are_blocked_without_network_requests(
    tmp_path,
    permission_status,
):
    source = Source(
        f"{SITE}/guide/restricted.pdf",
        "Example Docs",
        "Permission required",
        permission_status=permission_status,
    )

    site = FakeSite()

    counts = await site.run([source], tmp_path)

    assert counts["blocked"] == 1
    assert site.hits == []
    assert raw_files(tmp_path) == []

    record = manifest(tmp_path)[0]

    assert record["permission_status"] == permission_status
    assert record["status"] == "blocked"


async def test_approved_source_can_download(tmp_path):
    source = Source(
        f"{SITE}/guide/approved.pdf",
        "Example Docs",
        "Permission granted",
        permission_status="approved",
    )

    counts = await FakeSite().run([source], tmp_path)

    assert counts["downloaded"] == 1
    assert manifest(tmp_path)[0]["permission_status"] == "approved"
