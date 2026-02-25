from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_core import Agent, AgentRuntimeError
from http_schemas import AgentHandleRequest, AgentHandleResponse, HealthResponse
from telemetry import get_tracer, setup_telemetry

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class AgentHTTPSettings(BaseSettings):
    AGENT_CORE_HOST: str = "0.0.0.0"
    AGENT_CORE_PORT: int = 8100

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = AgentHTTPSettings()


def get_agent(request: Request) -> Agent:
    agent: Agent | None = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent runtime is not initialized")
    return agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the agent once so skills and MCP connection are reused across requests.
    agent = Agent()
    try:
        await agent.start()
        app.state.agent = agent
        yield
    finally:
        await agent.stop()


app = FastAPI(title="agent-core-http", lifespan=lifespan)
setup_telemetry(app=app, service_name="agent-core")
tracer = get_tracer(__name__)


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    agent = get_agent(request)
    return HealthResponse(status="ok", skills_loaded=len(agent.skills))


@app.get("/skills", response_model=list[dict[str, str]])
async def list_skills(request: Request) -> list[dict[str, str]]:
    agent = get_agent(request)
    return [
        {"name": skill.name, "description": skill.description}
        for skill in agent.skills.values()
    ]


@app.post("/agent/handle", response_model=AgentHandleResponse)
@app.post("/api/chat", response_model=AgentHandleResponse)
async def handle(payload: AgentHandleRequest, request: Request) -> AgentHandleResponse:
    agent = get_agent(request)
    with tracer.start_as_current_span("agent.http.handle") as span:
        span.set_attribute("question.length", len(payload.question))
        if payload.max_rows is not None:
            span.set_attribute("max_rows", payload.max_rows)
        try:
            result = await agent.handle(
                question=payload.question,
                max_rows=payload.max_rows,
                session_id=payload.session_id,
            )
        except AgentRuntimeError as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "AgentRuntimeError")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exc).__name__)
            raise HTTPException(status_code=500, detail=f"Agent processing failed: {exc}") from exc
        return AgentHandleResponse(**result)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "http_app:app",
        host=settings.AGENT_CORE_HOST,
        port=settings.AGENT_CORE_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
