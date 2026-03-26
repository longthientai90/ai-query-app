from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from service_schema.api.schemas import (
    HealthResponse,
    ReindexRequest,
    ReindexResponse,
    SchemaSearchRequest,
    SchemaSearchResponse,
    TableDetailResponse,
)
from service_schema.runtime import ServiceSchemaRuntime

router = APIRouter()


def get_runtime(request: Request) -> ServiceSchemaRuntime:
    runtime: ServiceSchemaRuntime | None = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=500, detail="service-schema runtime is not initialized")
    return runtime


@router.get("/schema/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    runtime = get_runtime(request)
    return HealthResponse(**runtime.health_response())


@router.post("/schema/reindex", response_model=ReindexResponse)
async def reindex(payload: ReindexRequest, request: Request) -> ReindexResponse:
    runtime = get_runtime(request)
    result = await runtime.reindex(include_indexes=payload.include_indexes)
    return ReindexResponse(**result)


@router.post("/schema/search", response_model=SchemaSearchResponse)
async def search(payload: SchemaSearchRequest, request: Request) -> SchemaSearchResponse:
    runtime = get_runtime(request)
    try:
        result = runtime.search(
            query=payload.query,
            max_tables=payload.max_tables,
            include_indexes=payload.include_indexes,
            include_relationships=payload.include_relationships,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SchemaSearchResponse(**result)


@router.get("/schema/tables/{table_name}", response_model=TableDetailResponse)
async def table_detail(table_name: str, request: Request) -> TableDetailResponse:
    runtime = get_runtime(request)
    try:
        table = runtime.get_table(table_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if table is None:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    return TableDetailResponse(**table)
