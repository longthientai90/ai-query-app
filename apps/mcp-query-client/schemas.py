from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    sql: str
    params: list[Any] | None = None
    max_rows: int | None = Field(default=None, gt=0)


class SchemaRequest(BaseModel):
    tables: list[str] | None = None
    include_indexes: bool = False


class ExplainRequest(BaseModel):
    sql: str
    params: list[Any] | None = None
    analyze: bool = False


class ChatRequest(BaseModel):
    question: str
    max_rows: int | None = Field(default=100, gt=0)
