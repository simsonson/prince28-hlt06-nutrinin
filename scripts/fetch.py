"""Collect your corpus. Four doors, one logbook (data/manifest.jsonl).

  uv run python scripts/fetch.py urls
  uv run python scripts/fetch.py repo OWNER/REPO ...
  uv run python scripts/fetch.py sitemap URL ...
  uv run python scripts/fetch.py manual FOLDER ...

Every collection method requires permission_status=approved
before collecting or registering source files.
"""

import argparse
import asyncio
import csv
import gzip
import hashlib
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from nutrinin.ingest.fetch import (
    USER_AGENT,
    Manifest,
    fetch_all,
    now_iso,
    read_sources,
    slug,
)

SOURCES = Path("data/sources.csv")
RAW = Path("data/raw")
MANIFEST = Path("data/manifest.jsonl")
HEADER = ["url", "source", "licence", "title", "permission_status"]
PERMISSION_STATUSES = ["approved", "pending", "denied", "unknown"]


def require_approved(permission_status: str) -> None:
    """Stop collection unless permission has explicitly been approved."""
    if permission_status != "approved":
        raise ValueError(
            f"Collection blocked: permission_status={permission_status!r}. "
            "Only 'approved' sources may be collected."
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def local_record(path: Path, **fields: str) -> dict:
    """A manifest line for a file already on disk."""
    size = path.stat().st_size
    digest = sha256_file(path)
    on_disk = {
        "path": path.as_posix(),
        "bytes": size,
        "sha256": digest,
    }
    return (
        fields
        | on_disk
        | {
            "status": "downloaded",
            "fetched_at": now_iso(),
        }
    )


# ---------- door 1: a list of URLs ----------


def cmd_urls(args: argparse.Namespace) -> int:
    sources = read_sources(args.sources)

    if args.limit:
        sources = sources[: args.limit]

    seen = 0

    def show(record: dict) -> None:
        nonlocal seen
        seen += 1

        if record["status"] == "downloaded":
            detail = f"{record['bytes'] / 1024:9.1f} kB  {record['path']}"
        else:
            detail = f"{record.get('error', '')}  {record['url']}"

        print(
            f"[{seen:>4}] {record['status']:<10} {detail}",
            flush=True,
        )

    started = time.perf_counter()

    counts = asyncio.run(
        fetch_all(
            sources,
            max_concurrency=args.max_concurrency,
            per_host_delay=args.delay,
            refresh=args.refresh,
            on_result=show,
        )
    )

    took = time.perf_counter() - started
    summary = " ".join(f"{name}={count}" for name, count in counts.items())

    print(f"sources={len(sources)} {summary} seconds={took:.1f}")
    return 0


# ---------- door 2: a Git repository ----------


def git(*args: str, cwd: Path | None = None) -> str:
    command = ["git", "-c", "core.longpaths=true", *args]
    env = os.environ | {"GIT_TERMINAL_PROMPT": "0"}

    done = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout


def cmd_repo(args: argparse.Namespace) -> int:
    require_approved(args.permission_status)

    repo = args.repo.removeprefix("https://github.com/").removesuffix(".git").strip("/")

    dest = RAW / slug(args.source)

    try:
        if not (dest / ".git").exists():
            dest.parent.mkdir(parents=True, exist_ok=True)

            clone = [
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
            ]

            if args.ref:
                clone += ["--branch", args.ref]

            git(
                *clone,
                f"https://github.com/{repo}.git",
                str(dest),
            )

        if args.path == ["."]:
            git("sparse-checkout", "disable", cwd=dest)
        else:
            git("sparse-checkout", "set", *args.path, cwd=dest)

        commit = git("rev-parse", "HEAD", cwd=dest).strip()

    except subprocess.CalledProcessError as exc:
        print(f"git failed: {exc.stderr.strip()}")
        print("Check the OWNER/REPO spelling, --path folders and your internet connection.")
        return 1

    wanted = {ext if ext.startswith(".") else "." + ext for ext in args.ext}

    manifest = Manifest(MANIFEST)
    added = unchanged = 0

    for folder in args.path:
        for path in sorted((dest / folder).rglob("*")):
            if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in wanted:
                continue

            inside = path.relative_to(dest).as_posix()

            record = local_record(
                path,
                url=f"https://github.com/{repo}/blob/HEAD/{inside}",
                source=args.source,
                licence=args.licence,
                permission_status=args.permission_status,
                title=inside,
                via="git",
                commit=commit,
            )

            old = manifest.records.get(record["url"], {})

            if old.get("sha256") == record["sha256"] and old.get("path") == record["path"]:
                unchanged += 1
            else:
                manifest.add(record)
                added += 1

    print(f"repo={repo} commit={commit[:10]} added={added} unchanged={unchanged}")
    return 0


# ---------- door 3: a sitemap ----------


def sitemap_urls(
    client: httpx.Client,
    url: str,
    depth: int = 0,
) -> list[str]:
    response = client.get(url)
    response.raise_for_status()

    body = response.content

    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)

    root = ET.fromstring(body)

    locs = [
        element.text.strip()
        for element in root.iter()
        if element.tag.endswith("loc") and element.text
    ]

    if root.tag.endswith("sitemapindex") and depth < 2:
        return [page for child in locs[:50] for page in sitemap_urls(client, child, depth + 1)]

    return locs


def cmd_sitemap(args: argparse.Namespace) -> int:
    headers = {"User-Agent": USER_AGENT}

    with httpx.Client(
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        try:
            found = sitemap_urls(client, args.url)
        except (httpx.HTTPError, ET.ParseError, OSError) as exc:
            print(f"could not read the sitemap: {exc}")
            return 1

    keep = [url for url in found if all(word in url for word in args.include)]

    keep = [url for url in keep if not any(word in url for word in args.exclude)]

    have: set[str] = set()

    if SOURCES.exists():
        with SOURCES.open(
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(
                line for line in handle if line.strip() and not line.lstrip().startswith("#")
            )
            have = {(row.get("url") or "").strip() for row in reader}

    new = [url for url in dict.fromkeys(keep) if url not in have]

    if args.limit:
        new = new[: args.limit]

    SOURCES.parent.mkdir(parents=True, exist_ok=True)
    first_time = not SOURCES.exists()

    with SOURCES.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)

        if first_time:
            writer.writerow(HEADER)

        writer.writerows(
            [
                url,
                args.source,
                args.licence,
                "",
                args.permission_status,
            ]
            for url in new
        )

    print(f"sitemap_urls={len(found)} matched={len(keep)} added_to_sources={len(new)}")
    return 0


# ---------- door 4: files downloaded by hand ----------


def cmd_manual(args: argparse.Namespace) -> int:
    require_approved(args.permission_status)

    folder = args.folder.resolve()

    if not folder.is_dir() or not folder.is_relative_to(RAW.resolve()):
        print(f"put the files in a folder under {RAW.as_posix()}/ first, e.g. data/raw/my-source")
        return 1

    manifest = Manifest(MANIFEST)
    known = {record.get("path") for record in manifest.records.values()}

    added = 0

    for file in sorted(folder.rglob("*")):
        path = file.relative_to(Path.cwd())

        if not file.is_file() or file.name.startswith(".") or path.as_posix() in known:
            continue

        record = local_record(
            path,
            url=f"{args.from_url}#{file.name}",
            source=args.source,
            licence=args.licence,
            permission_status=args.permission_status,
            title=file.stem,
            via="manual",
        )

        manifest.add(record)
        added += 1

    print(f"folder={args.folder.as_posix()} added={added}")
    return 0


# ---------- command-line interface ----------


def add_permission_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--permission-status",
        choices=PERMISSION_STATUSES,
        default="unknown",
        help="permission status (default: unknown; collection blocked)",
    )


def main() -> int:
    sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    doors = parser.add_subparsers(
        dest="door",
        required=True,
    )

    # URLs
    urls = doors.add_parser(
        "urls",
        help="download URLs in data/sources.csv",
    )
    urls.add_argument("--sources", type=Path, default=SOURCES)
    urls.add_argument(
        "--max-concurrency",
        type=int,
        default=4,
        help="downloads at once (default 4)",
    )
    urls.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="seconds between hits on one site",
    )
    urls.add_argument(
        "--limit",
        type=int,
        default=0,
        help="only the first N sources",
    )
    urls.add_argument(
        "--refresh",
        action="store_true",
        help="revalidate downloaded URLs with If-None-Match when an ETag is available",
    )
    urls.set_defaults(run=cmd_urls)

    # Git repository
    repo = doors.add_parser(
        "repo",
        help="clone folders from a GitHub repository",
    )
    repo.add_argument("repo", help="OWNER/REPO")
    repo.add_argument(
        "--path",
        action="append",
        required=True,
        help="folder in the repository (repeat)",
    )
    repo.add_argument(
        "--ext",
        action="append",
        required=True,
        help="file type to keep, e.g. .md",
    )
    repo.add_argument(
        "--source",
        required=True,
        help="short name for the source folder",
    )
    repo.add_argument("--licence", required=True)
    add_permission_argument(repo)
    repo.add_argument(
        "--ref",
        default="",
        help="branch or tag (default: default branch)",
    )
    repo.set_defaults(run=cmd_repo)

    # Sitemap
    sitemap = doors.add_parser(
        "sitemap",
        help="add sitemap URLs to data/sources.csv",
    )
    sitemap.add_argument("url", help="sitemap URL")
    sitemap.add_argument(
        "--include",
        action="append",
        default=[],
        help="URL must contain this",
    )
    sitemap.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="URL must not contain this",
    )
    sitemap.add_argument("--limit", type=int, default=0)
    sitemap.add_argument("--source", required=True)
    sitemap.add_argument("--licence", required=True)
    add_permission_argument(sitemap)
    sitemap.set_defaults(run=cmd_sitemap)

    # Manual files
    manual = doors.add_parser(
        "manual",
        help="register files downloaded by hand",
    )
    manual.add_argument(
        "folder",
        type=Path,
        help="a folder under data/raw/",
    )
    manual.add_argument(
        "--from-url",
        required=True,
        help="the page the files came from",
    )
    manual.add_argument("--source", required=True)
    manual.add_argument("--licence", required=True)
    add_permission_argument(manual)
    manual.set_defaults(run=cmd_manual)

    args = parser.parse_args()

    try:
        return args.run(args)

    except KeyboardInterrupt:
        print("\nStopped. Run the same command again: finished files are skipped.")
        return 130

    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
