from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request

from agent_core_client import AgentCoreClient, AgentCoreClientError
from telemetry import get_tracer

tracer = get_tracer(__name__)


def get_agent_core_client(request: Request) -> AgentCoreClient:
    client: AgentCoreClient | None = getattr(request.app.state, "agent_core_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="Agent-core client is not initialized")
    return client


async def process_agent_core_request(
    *,
    request: Request,
    question: str,
    max_rows: int | None,
    session_id: str | None,
    span_name: str,
    response_factory: Callable[..., object],
):
    client = get_agent_core_client(request)
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("question.length", len(question))
        if max_rows is not None:
            span.set_attribute("max_rows", max_rows)
        try:
            result = await client.handle(
                question=question,
                max_rows=max_rows,
                session_id=session_id,
            )
        except AgentCoreClientError as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "AgentCoreClientError")
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except Exception as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exc).__name__)
            raise HTTPException(status_code=500, detail=f"Gateway processing failed: {exc}") from exc
        return response_factory(**result)
