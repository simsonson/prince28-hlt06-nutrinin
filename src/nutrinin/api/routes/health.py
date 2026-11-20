"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Response

from nutrinin.api.deps import DbCheckDep, RepoDep, SettingsDep

router = APIRouter(tags=["health"])

MIN_EXPECTED_RECORDS = 20


@router.api_route(
    "/health",
    methods=["GET", "HEAD"],
)
def health(settings: SettingsDep) -> dict[str, str]:
    """Liveness: is the process alive? Never touches the DB."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": settings.git_sha,
    }


@router.get("/ready")
async def ready(
    db_ok: DbCheckDep,
    repo: RepoDep,
    response: Response,
) -> dict:
    """Readiness: can this instance serve traffic right now?"""

    records_count = 0

    if db_ok:
        try:
            records_count = await repo.count_records()
        except Exception:
            db_ok = False

    checks = {
        "database": db_ok,
        "records_loaded": records_count >= MIN_EXPECTED_RECORDS,
    }

    is_ready = all(checks.values())

    if not is_ready:
        response.status_code = 503

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "records_count": records_count,
    }
