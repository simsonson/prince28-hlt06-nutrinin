"""Report parsing coverage from the documents and parse_failures tables.

Run with: uv run python scripts/parse_coverage.py
"""

import asyncio

from sqlalchemy import text

from nutrinin.config import get_settings
from nutrinin.db.session import make_engine

COVERAGE_QUERY = text(
    """
    WITH counts AS (
        SELECT
            (SELECT count(*) FROM documents WHERE doc_type <> 'record') AS parsed_files,
            (SELECT count(*) FROM parse_failures) AS failed_files,
            (SELECT count(*) FROM pages) AS parsed_pages,
            (
                SELECT coalesce(sum((substring(detail FROM 'on ([0-9]+) pages'))::int), 0)
                FROM parse_failures
                WHERE detail ~ 'on [0-9]+ pages'
            ) AS failed_pages
    )
    SELECT
        parsed_files,
        failed_files,
        round(100.0 * parsed_files / nullif(parsed_files + failed_files, 0)) AS files_pct,
        parsed_pages,
        failed_pages,
        round(100.0 * parsed_pages / nullif(parsed_pages + failed_pages, 0)) AS pages_pct
    FROM counts
    """
)


async def main() -> None:
    engine = make_engine(get_settings())
    async with engine.connect() as connection:
        row = (await connection.execute(COVERAGE_QUERY)).mappings().one()
    await engine.dispose()
    print(dict(row))


if __name__ == "__main__":
    asyncio.run(main())
