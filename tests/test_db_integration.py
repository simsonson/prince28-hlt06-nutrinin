"""Runs against a REAL Postgres. Skipped unless TEST_DATABASE_URL is set.

Use an empty database you don't mind wiping, e.g. a second Neon database "test".
"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from nutrinin.api.main import create_app
from nutrinin.config import Settings
from nutrinin.db.models import Base, Document
from nutrinin.db.session import make_engine, make_sessionmaker

TEST_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="set TEST_DATABASE_URL to run")


async def _reset_and_seed(settings: Settings) -> None:
    engine = make_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as session, session.begin():
        session.add_all(
            [
                Document(external_id="001", title="Alpha", sha256="a" * 64, metadata_={"k": "x"}),
                Document(external_id="002", title="Beta", sha256="b" * 64, metadata_={"k": "y"}),
            ]
        )
    await engine.dispose()


@pytest.fixture(scope="module")
def db_client():
    settings = Settings(app_env="ci", database_url=TEST_URL, _env_file=None)
    asyncio.run(_reset_and_seed(settings))
    with TestClient(create_app(settings)) as c:
        yield c


def test_ready_reports_real_record_count(db_client):
    response = db_client.get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] is True
    assert response.json()["records_count"] == 2
    assert response.json()["status"] == "not_ready"


def test_stats_with_real_database(db_client):
    assert db_client.get("/v1/stats").json() == {
        "records_count": 2,
        "by_doc_type": {"record": 2},
    }


def test_filter_uses_jsonb_containment(db_client):
    body = db_client.get("/v1/documents", params={"k": "y"}).json()
    assert [d["id"] for d in body["items"]] == ["002"]


def test_get_from_real_database(db_client):
    assert db_client.get("/v1/documents/001").json()["title"] == "Alpha"
