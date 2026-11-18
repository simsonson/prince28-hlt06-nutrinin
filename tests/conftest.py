import pytest
from fastapi.testclient import TestClient

from nutrinin.api.deps import check_db, get_repo
from nutrinin.api.main import create_app
from nutrinin.config import Settings

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

    async def count_records(self):
        return len(self.rows)

    async def count_by_doc_type(self):
        counts = {}
        for row in self.rows:
            doc_type = row.get("doc_type", "record")
            counts[doc_type] = counts.get(doc_type, 0) + 1
        return counts


@pytest.fixture
def settings():
    # _env_file=None: ignore your local .env so tests behave the same everywhere
    return Settings(app_env="ci", database_url="postgresql://localhost:5432/unused", _env_file=None)


@pytest.fixture
def db_state():
    return {"up": True}


@pytest.fixture
def client(settings, db_state):
    app = create_app(settings)
    app.dependency_overrides[get_repo] = lambda: FakeRepo(SAMPLE)
    app.dependency_overrides[check_db] = lambda: db_state["up"]
    with TestClient(app) as c:
        yield c
