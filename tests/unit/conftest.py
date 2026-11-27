import pytest
from fastapi.testclient import TestClient

from nutrinin.api.deps import (
    check_db,
    get_gateway,
    get_ingest_repo,
    get_manifest,
    get_queue,
    get_repo,
    get_usage_repo,
)
from nutrinin.api.main import create_app
from nutrinin.config import Settings
from nutrinin.llm.gateway import FakeLLM, LLMGateway

# Tiny fake records: unit tests never touch a real database or your data file.
SAMPLE = [
    {
        "id": "001",
        "title": "Alpha guideline",
        "year": 2023,
        "kind": "guideline",
        "food_code": "H001",
        "doc_type": "guideline",
    },
    {
        "id": "002",
        "title": "Beta circular",
        "year": 2024,
        "kind": "circular",
        "food_code": "H002",
        "doc_type": "circular",
    },
    {
        "id": "003",
        "title": "Gamma notice",
        "year": 2025,
        "kind": "circular",
        "food_code": "H003",
        "doc_type": "circular",
    },
    *[
        {
            "id": f"{i:03}",
            "title": f"Food {i:03}",
            "doc_type": "record",
            "food_code": f"H{i:03}",
            "food_name": f"Food {i:03}",
            "energy_kcal": 100,
            "protein_g": 5.0,
            "iron_mg": None,
            "fibre_g": 2.0,
            "per_100g": True,
            "source": "test",
        }
        for i in range(4, 21)
    ],
]


class FakeRepo:
    """Behaves like DocumentRepository, but keeps rows in a Python list."""

    def __init__(self, rows):
        self.rows = rows
        self.pages = {
            ("001", 2): {"page_no": 2, "text": "Review after two days.", "headings": ["Fever"]}
        }

    async def list(self, *, q, filters, food_code, sort, limit, offset):
        rows = [
            r
            for r in self.rows
            if (not q or q.lower() in str(r).lower())
            and (food_code is None or r.get("food_code") == food_code)
            and all(str(r.get(k)) == v for k, v in filters.items())
        ]
        sort_key = sort.removeprefix("-")
        field = "id" if sort_key == "id" else sort_key
        rows.sort(
            key=lambda row: (row.get(field) is None, row.get(field)),
            reverse=sort.startswith("-"),
        )
        return len(rows), rows[offset : offset + limit]

    async def get(self, external_id):
        return next((r for r in self.rows if r["id"] == external_id), None)

    async def get_page(self, external_id, page_no):
        return self.pages.get((external_id, page_no))

    async def count_records(self):
        return len(self.rows)

    async def count_by_doc_type(self):
        counts = {}
        for row in self.rows:
            doc_type = row.get("doc_type", "record")
            counts[doc_type] = counts.get(doc_type, 0) + 1
        return counts


class FakeUsageRepo:
    """Returns predictable usage data without connecting to PostgreSQL."""

    async def by_day(self, days: int = 7) -> list[dict]:
        return [
            {
                "day": "2026-11-26",
                "calls": 3,
                "errors": 0,
                "fallbacks": 0,
                "tokens_in": 300,
                "tokens_out": 120,
                "cost_inr": 0.0642,
            }
        ]


@pytest.fixture
def settings():
    # _env_file=None: ignore your local .env so tests behave the same everywhere
    return Settings(
        app_env="ci",
        database_url="postgresql://localhost:5432/unused",
        admin_token="test-token",
        _env_file=None,
    )


@pytest.fixture
def db_state():
    return {"up": True}


@pytest.fixture
def llm():
    """A scripted fake model; no API calls or external network."""
    return FakeLLM()


@pytest.fixture
def usage_repo():
    """Fake usage repository; no PostgreSQL connection."""
    return FakeUsageRepo()


@pytest.fixture
def queue():
    class FakeQueue:
        def __init__(self):
            self.items = []

        async def put(self, item_ids):
            self.items += item_ids
            return len(item_ids)

    return FakeQueue()


@pytest.fixture
def ingest_repo():
    from tests.conftest import FakeIngestRepo

    return FakeIngestRepo()


@pytest.fixture
def manifest():
    def record(n: int, **changes):
        return {
            "url": f"https://x.test/{n}.pdf",
            "source": "x",
            "licence": "CC BY 4.0",
            "path": f"data/raw/x/{n}.pdf",
            "sha256": str(n) * 64,
            "status": "downloaded",
            **changes,
        }

    return [record(1), record(2), record(3, sha256="a" * 64), record(4, status="failed")]


@pytest.fixture
def client(settings, db_state, llm, usage_repo, queue, ingest_repo, manifest):
    app = create_app(settings)

    app.dependency_overrides[get_repo] = lambda: FakeRepo(SAMPLE)
    app.dependency_overrides[check_db] = lambda: db_state["up"]

    app.dependency_overrides[get_gateway] = lambda: LLMGateway([llm])
    app.dependency_overrides[get_usage_repo] = lambda: usage_repo
    app.dependency_overrides[get_queue] = lambda: queue
    app.dependency_overrides[get_ingest_repo] = lambda: ingest_repo
    app.dependency_overrides[get_manifest] = lambda: manifest

    with TestClient(app) as c:
        yield c
