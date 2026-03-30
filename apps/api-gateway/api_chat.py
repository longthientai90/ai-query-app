from __future__ import annotations

from fastapi import APIRouter, Request

from common import process_agent_core_request
from schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    return await process_agent_core_request(
        request=request,
        question=payload.question,
        max_rows=payload.max_rows,
        session_id=payload.session_id,
        span_name="gateway.chat.process",
        response_factory=ChatResponse,
    )
