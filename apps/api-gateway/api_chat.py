from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agent_core_client import AgentCoreClient, AgentCoreClientError
from schemas import ChatRequest, ChatResponse
from telemetry import get_tracer

router = APIRouter(prefix="/api", tags=["chat"])
tracer = get_tracer(__name__)


def get_agent_core_client(request: Request) -> AgentCoreClient:
    client: AgentCoreClient | None = getattr(request.app.state, "agent_core_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="Agent-core client is not initialized")
    return client


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    client = get_agent_core_client(request)
    with tracer.start_as_current_span("gateway.chat.process") as span:
        span.set_attribute("question.length", len(payload.question))
        if payload.max_rows is not None:
            span.set_attribute("max_rows", payload.max_rows)
        try:
            result = await client.handle(
                question=payload.question,
                max_rows=payload.max_rows,
                session_id=payload.session_id,
            )
        except AgentCoreClientError as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "AgentCoreClientError")
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except Exception as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exc).__name__)
            raise HTTPException(status_code=500, detail=f"Gateway processing failed: {exc}") from exc
        return ChatResponse(**result)
