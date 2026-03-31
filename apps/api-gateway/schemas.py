from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    max_rows: int | None = Field(default=None, gt=0)
    session_id: str | None = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    selected_skill: str
    session_id: str
    sql: str | None = None
    params: list[Any] | None = None
    result: dict[str, Any] | None = None
    router_reason: str | None = None


class SearchRequest(BaseModel):
    question: str = Field(min_length=1)
    max_rows: int | None = Field(default=None, gt=0)
    session_id: str | None = None


class SearchResponse(BaseModel):
    question: str
    answer: str
    selected_skill: str
    session_id: str
    sql: str | None = None
    params: list[Any] | None = None
    result: dict[str, Any] | None = None
    router_reason: str | None = None


class ChartSuggestRequest(BaseModel):
    question: str = Field(min_length=1)
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int | None = Field(default=None, ge=0)


class ChartSuggestion(BaseModel):
    type: str
    title: str
    reason: str
    x_column: str
    y_column: str


class ChartSuggestResponse(BaseModel):
    can_chart: bool
    summary: str
    suggestions: list[ChartSuggestion] = Field(default_factory=list)


class ChartRenderRequest(BaseModel):
    question: str = Field(min_length=1)
    chart_type: str = Field(min_length=1)
    x_column: str = Field(min_length=1)
    y_column: str = Field(min_length=1)
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ChartSeriesPoint(BaseModel):
    label: str
    value: float


class ChartRenderResponse(BaseModel):
    chart_type: str
    title: str
    x_column: str
    y_column: str
    summary: str
    html_snippet: str | None = None
    points: list[ChartSeriesPoint] = Field(default_factory=list)
