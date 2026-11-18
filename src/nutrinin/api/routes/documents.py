from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

from nutrinin.api.deps import RepoDep
from nutrinin.db.repository import FILTER_KEY, SORT_COLUMNS

router = APIRouter(prefix="/documents", tags=["documents"])
stats_router = APIRouter(tags=["stats"])


class Record(BaseModel):
    """A food composition record returned by the API."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    doc_type: str
    source_url: str | None = None
    licence: str | None = None
    published_on: str | None = None
    food_code: str | None = None
    food_name: str | None = None
    energy_kcal: float | None = None
    protein_g: float | None = None
    iron_mg: float | None = None
    fibre_g: float | None = None
    per_100g: bool | None = None
    source: str | None = None


class DocumentList(BaseModel):
    total: int
    limit: int
    offset: int
    filters: dict[str, str]
    items: list[Record]


class DocumentStats(BaseModel):
    records_count: int
    by_doc_type: dict[str, int]


RESERVED = {"q", "limit", "offset", "food_code", "sort"}


@router.get("", response_model=DocumentList)
async def list_documents(
    request: Request,
    repo: RepoDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    food_code: Annotated[str | None, Query(max_length=40)] = None,
    sort: Annotated[str, Query(max_length=40)] = "id",
) -> dict:
    """Any other query parameter filters on a metadata field, e.g. ?dosage_form=Tablet"""
    filters = {k: v for k, v in request.query_params.items() if k not in RESERVED}
    sort_key = sort.removeprefix("-")
    if sort_key not in SORT_COLUMNS or sort.startswith("--"):
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort}")
    bad = [k for k in filters if not FILTER_KEY.match(k)]
    if bad:
        raise HTTPException(status_code=400, detail=f"Invalid filter name: {bad[0]}")
    total, items = await repo.list(
        q=q,
        filters=filters,
        food_code=food_code,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {"total": total, "limit": limit, "offset": offset, "filters": filters, "items": items}


@stats_router.get("/stats", response_model=DocumentStats)
async def document_stats(repo: RepoDep) -> dict:
    return {
        "records_count": await repo.count_records(),
        "by_doc_type": await repo.count_by_doc_type(),
    }


@router.get("/{doc_id}", response_model=Record)
async def get_document(doc_id: str, repo: RepoDep) -> dict:
    record = await repo.get(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{doc_id}'.")
    return record
