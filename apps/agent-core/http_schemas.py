from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentHandleRequest(BaseModel):
    question: str = Field(min_length=1)
    max_rows: int | None = Field(default=None, gt=0)
    session_id: str | None = None


class AgentHandleResponse(BaseModel):
    question: str
    answer: str
    selected_skill: str
    session_id: str
    sql: str | None = None
    params: list[Any] | None = None
    result: dict[str, Any] | None = None
    router_reason: str | None = None


class HealthResponse(BaseModel):
    status: str
    skills_loaded: int
