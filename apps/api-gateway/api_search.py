from __future__ import annotations

from fastapi import APIRouter, Request

from common import process_agent_core_request
from schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(payload: SearchRequest, request: Request) -> SearchResponse:
    return await process_agent_core_request(
        request=request,
        question=payload.question,
        max_rows=payload.max_rows,
        session_id=payload.session_id,
        span_name="gateway.search.process",
        response_factory=SearchResponse,
    )
