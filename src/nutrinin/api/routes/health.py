from fastapi import APIRouter, Response

from nutrinin.api.deps import DbCheckDep, RepoDep, SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    """Liveness: is the process alive? Instant. Never touches the DB or the LLM."""
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


MIN_RECORDS = 20


@router.get("/ready")
async def ready(db_ok: DbCheckDep, repo: RepoDep, response: Response) -> dict:
    """Readiness: can this instance serve traffic right now?"""
    records_count = await repo.count_records() if db_ok else 0
    checks = {"database": db_ok, "records_loaded": records_count >= MIN_RECORDS}
    ok = all(checks.values())
    if not ok:
        response.status_code = 503
    return {
        "status": "ready" if ok else "not_ready",
        "checks": checks,
        "records_count": records_count,
    }
