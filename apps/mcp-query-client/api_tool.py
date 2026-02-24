from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from mcp_service import MCPService, MCPServiceError
from schemas import ExplainRequest, QueryRequest, SchemaRequest

router = APIRouter()


def get_mcp_service(request: Request) -> MCPService:
    service: MCPService | None = getattr(request.app.state, "mcp_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="MCP service is not ready")
    return service


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/tools")
async def list_tools(request: Request) -> dict:
    service = get_mcp_service(request)
    try:
        return await service.list_tools()
    except MCPServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to list tools") from exc


@router.post("/query")
async def query(payload: QueryRequest, request: Request) -> dict:
    service = get_mcp_service(request)
    try:
        return await service.call_tool(
            "postgres_query",
            {
                "sql": payload.sql,
                "params": payload.params,
                "max_rows": payload.max_rows,
            },
        )
    except MCPServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to call postgres_query") from exc


@router.post("/schema")
async def schema(payload: SchemaRequest, request: Request) -> dict:
    service = get_mcp_service(request)
    try:
        return await service.call_tool(
            "postgres_get_schema",
            {
                "tables": payload.tables,
                "include_indexes": payload.include_indexes,
            },
        )
    except MCPServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to call postgres_get_schema") from exc


@router.post("/explain")
async def explain(payload: ExplainRequest, request: Request) -> dict:
    service = get_mcp_service(request)
    try:
        return await service.call_tool(
            "postgres_explain",
            {
                "sql": payload.sql,
                "params": payload.params,
                "analyze": payload.analyze,
            },
        )
    except MCPServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to call postgres_explain") from exc

