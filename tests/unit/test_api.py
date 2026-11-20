import pytest
from pydantic import ValidationError

from nutrinin.config import Settings
from nutrinin.db.url import to_asyncpg_url


def test_health_is_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["version"] == "dev"  # no GIT_SHA outside a CI-built image


def test_git_sha_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("GIT_SHA", "3f2c1ab")
    settings = Settings(app_env="ci", database_url="postgresql://localhost/db", _env_file=None)
    assert settings.git_sha == "3f2c1ab"


def test_ready_when_database_up(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["checks"]["database"] is True
    assert r.json()["records_count"] == 20
    assert r.json()["status"] == "ready"


def test_ready_is_503_when_too_few_records(client):
    from nutrinin.api.deps import get_repo

    repo = client.app.dependency_overrides[get_repo]()
    repo.rows = repo.rows[:-1]
    client.app.dependency_overrides[get_repo] = lambda: repo
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.json()["records_count"] == 19
    assert r.json()["checks"]["records_loaded"] is False


def test_ready_is_503_when_database_down(client, db_state):
    db_state["up"] = False
    assert client.get("/health").status_code == 200  # alive...
    assert client.get("/ready").status_code == 503  # ...but not ready


def test_list_documents_paginates(client):
    body = client.get("/v1/documents", params={"limit": 2}).json()
    assert body["total"] == 20
    assert len(body["items"]) == 2


def test_search_filters_records(client):
    r = client.get("/v1/documents", params={"q": "beta"})
    assert [d["id"] for d in r.json()["items"]] == ["002"]


def test_metadata_filter(client):
    r = client.get("/v1/documents", params={"kind": "circular"})
    assert r.json()["total"] == 2
    assert r.json()["filters"] == {"kind": "circular"}


def test_food_code_filter(client):
    r = client.get("/v1/documents", params={"food_code": "H001"})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["food_code"] == "H001"


def test_list_documents_sorts_by_known_column(client):
    body = client.get("/v1/documents", params={"sort": "title", "limit": 3}).json()
    assert [item["id"] for item in body["items"]] == ["001", "002", "004"]


def test_list_documents_rejects_unknown_sort_column(client):
    response = client.get("/v1/documents", params={"sort": "metadata"})
    assert response.status_code == 400


def test_document_stats(client):
    r = client.get("/v1/stats")
    assert r.status_code == 200
    assert r.json() == {
        "records_count": 20,
        "by_doc_type": {"guideline": 1, "circular": 2, "record": 17},
    }


def test_record_response_schema_is_exposed(client):
    schema = client.get("/openapi.json").json()
    record = schema["components"]["schemas"]["Record"]["properties"]
    expected_fields = {
        "food_code",
        "food_name",
        "energy_kcal",
        "protein_g",
        "iron_mg",
        "fibre_g",
    }
    assert expected_fields <= set(record)


def test_invalid_filter_name_is_400(client):
    r = client.get("/v1/documents", params={"Bad-Key": "x"})
    assert r.status_code == 400
    assert r.headers["content-type"] == "application/problem+json"


def test_get_document_found(client):
    r = client.get("/v1/documents/001")
    assert r.status_code == 200
    assert r.json()["title"] == "Alpha guideline"


def test_missing_document_is_problem_details(client):
    r = client.get("/v1/documents/999")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["request_id"] == r.headers["X-Request-ID"]


def test_bad_limit_is_422_problem(client):
    r = client.get("/v1/documents", params={"limit": 0})
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "query.limit"


def test_request_id_is_echoed(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"


@pytest.mark.parametrize("missing", ["APP_ENV", "DATABASE_URL"])
def test_app_refuses_to_start_without_required_settings(monkeypatch, missing):
    monkeypatch.setenv("APP_ENV", "ci")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")
    monkeypatch.delenv(missing)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql://app@ep-x.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://app@ep-x.neon.tech/neondb?ssl=require",
        ),
        (
            "postgresql://postgres@localhost:5432/app?sslmode=disable",
            "postgresql+asyncpg://postgres@localhost:5432/app",
        ),
        ("postgres://app@h/db", "postgresql+asyncpg://app@h/db"),
    ],
)
def test_database_url_is_converted_for_asyncpg(raw, expected):
    assert to_asyncpg_url(raw) == expected
