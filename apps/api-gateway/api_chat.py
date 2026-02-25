from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])


def get_agent(request: Request) -> Any:
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent runtime is not initialized")
    return agent


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    agent = get_agent(request)
    try:
        result = await agent.handle(
            question=payload.question,
            max_rows=payload.max_rows,
            session_id=payload.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {exc}") from exc
    return ChatResponse(**result)
