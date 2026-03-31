from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from schemas import (
    ChartRenderRequest,
    ChartRenderResponse,
    ChartSeriesPoint,
    ChartSuggestRequest,
    ChartSuggestResponse,
    ChartSuggestion,
)

router = APIRouter(prefix="/api/chart", tags=["chart"])

MAX_SAMPLE_ROWS = 20
MAX_RENDER_ROWS = 100


@router.post("/suggest", response_model=ChartSuggestResponse)
async def suggest_chart(payload: ChartSuggestRequest, request: Request) -> ChartSuggestResponse:
    columns = [column for column in payload.columns if isinstance(column, str) and column.strip()]
    sample_rows = payload.rows[:MAX_SAMPLE_ROWS]
    heuristic_suggestions = build_heuristic_suggestions(columns, sample_rows)
    fallback_summary: str | None = None

    llm_service = getattr(request.app.state, "chart_llm_service", None)
    if llm_service is not None:
        try:
            can_chart, summary, suggestions = await llm_service.suggest_chart(
                question=payload.question,
                columns=columns,
                rows=sample_rows,
                heuristic_suggestions=heuristic_suggestions,
            )
            return ChartSuggestResponse(can_chart=can_chart, summary=summary, suggestions=suggestions)
        except Exception as exc:
            fallback_summary = f"Azure chart suggestion unavailable. Falling back to rule-based suggestions. ({exc})"

    if heuristic_suggestions:
        summary = fallback_summary or (
            f"Found {len(heuristic_suggestions)} chart option(s) from the returned table based on column types and sample values."
        )
        return ChartSuggestResponse(can_chart=True, summary=summary, suggestions=heuristic_suggestions)

    return ChartSuggestResponse(
        can_chart=False,
        summary=fallback_summary or "This table looks more like detailed records than chart-friendly grouped data.",
        suggestions=[],
    )


@router.post("/render", response_model=ChartRenderResponse)
async def render_chart(payload: ChartRenderRequest, request: Request) -> ChartRenderResponse:
    chart_type = payload.chart_type.strip().lower()
    if chart_type not in {"bar", "line"}:
        raise HTTPException(status_code=400, detail="Only bar and line charts are supported right now.")

    rows = payload.rows[:MAX_RENDER_ROWS]
    points = build_chart_points(rows, payload.x_column, payload.y_column)
    if not points:
        raise HTTPException(status_code=400, detail="Not enough usable rows to render this chart.")

    title_connector = "over" if chart_type == "line" else "by"
    chart_config = build_chartjs_config(
        chart_type=chart_type,
        title=f"{format_label(payload.y_column)} {title_connector} {format_label(payload.x_column)}",
        x_column=payload.x_column,
        y_column=payload.y_column,
        points=points,
    )

    chart_mcp_service = getattr(request.app.state, "chart_mcp_service", None)
    html_snippet: str | None = None
    if chart_mcp_service is not None:
        try:
            html_snippet = await chart_mcp_service.render_chart_html(chart_config=chart_config)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Chart MCP render failed: {exc}") from exc

    return ChartRenderResponse(
        chart_type=chart_type,
        title=f"{format_label(payload.y_column)} {title_connector} {format_label(payload.x_column)}",
        x_column=payload.x_column,
        y_column=payload.y_column,
        summary=f"Rendered {len(points)} point(s) using Azure-guided suggestion and Chart.js MCP rendering.",
        html_snippet=html_snippet,
        points=points,
    )


def analyze_columns(columns: list[str], rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    analysis: list[dict[str, str]] = []
    for column in columns:
        values = [row.get(column) for row in rows if isinstance(row, dict) and column in row]
        kind = infer_column_kind(column, values)
        analysis.append({"name": column, "kind": kind})
    return analysis


def build_heuristic_suggestions(columns: list[str], rows: list[dict[str, Any]]) -> list[ChartSuggestion]:
    analysis = analyze_columns(columns, rows)
    numeric_columns = [item["name"] for item in analysis if item["kind"] == "numeric"]
    time_columns = [item["name"] for item in analysis if item["kind"] == "time"]
    categorical_columns = [item["name"] for item in analysis if item["kind"] == "categorical"]

    suggestions: list[ChartSuggestion] = []

    if time_columns and numeric_columns:
        x_column = time_columns[0]
        y_column = numeric_columns[0]
        suggestions.append(
            ChartSuggestion(
                type="line",
                title=f"{format_label(y_column)} over {format_label(x_column)}",
                reason="Detected a time-like column paired with a numeric metric.",
                x_column=x_column,
                y_column=y_column,
            )
        )

    if numeric_columns and (categorical_columns or time_columns):
        x_candidates = categorical_columns or time_columns
        x_column = x_candidates[0]
        y_column = numeric_columns[0]
        if not any(
            suggestion.type == "bar"
            and suggestion.x_column == x_column
            and suggestion.y_column == y_column
            for suggestion in suggestions
        ):
            suggestions.append(
                ChartSuggestion(
                    type="bar",
                    title=f"{format_label(y_column)} by {format_label(x_column)}",
                    reason="Detected one grouping column and one numeric metric suited for comparison.",
                    x_column=x_column,
                    y_column=y_column,
                )
            )

    return suggestions


def build_chart_points(rows: list[dict[str, Any]], x_column: str, y_column: str) -> list[ChartSeriesPoint]:
    points: list[ChartSeriesPoint] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        label_value = row.get(x_column)
        numeric_value = to_number(row.get(y_column))
        if numeric_value is None:
            continue

        label = str(label_value).strip() if label_value is not None else ""
        if not label:
            continue

        points.append(ChartSeriesPoint(label=label, value=numeric_value))

    return points


def build_chartjs_config(
    *,
    chart_type: str,
    title: str,
    x_column: str,
    y_column: str,
    points: list[ChartSeriesPoint],
) -> dict[str, Any]:
    if chart_type == "line":
        sorted_points = sort_chart_points(points)
    else:
        sorted_points = points

    labels = [point.label for point in sorted_points]
    values = [point.value for point in sorted_points]

    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": format_label(y_column),
                    "data": values,
                    "backgroundColor": "rgba(20, 184, 166, 0.78)",
                    "borderColor": "rgba(15, 118, 110, 1)",
                    "borderWidth": 2,
                    "fill": False,
                    "tension": 0.25,
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title,
                },
                "legend": {
                    "display": True,
                },
            },
            "scales": {
                "x": {
                    "title": {
                        "display": True,
                        "text": format_label(x_column),
                    }
                },
                "y": {
                    "beginAtZero": True,
                    "title": {
                        "display": True,
                        "text": format_label(y_column),
                    }
                },
            },
        },
    }


def sort_chart_points(points: list[ChartSeriesPoint]) -> list[ChartSeriesPoint]:
    if len(points) < 2:
        return points

    time_values = [parse_time_like_label(point.label) for point in points]
    if all(value is not None for value in time_values):
        return [point for _, point in sorted(zip(time_values, points), key=lambda item: item[0])]

    numeric_values = [to_number(point.label) for point in points]
    if all(value is not None for value in numeric_values):
        return [point for _, point in sorted(zip(numeric_values, points), key=lambda item: item[0])]

    return points


def infer_column_kind(column_name: str, values: list[Any]) -> str:
    non_empty_values = [value for value in values if value not in (None, "")]
    normalized_name = column_name.lower()

    if any(token in normalized_name for token in ("date", "time", "month", "year", "day")):
        return "time"

    if non_empty_values and is_mostly_numeric(non_empty_values):
        return "numeric"

    if non_empty_values and is_mostly_time(non_empty_values):
        return "time"

    return "categorical"


def is_mostly_numeric(values: list[Any]) -> bool:
    successes = sum(1 for value in values if to_number(value) is not None)
    return successes >= max(1, len(values) // 2 + 1)


def is_mostly_time(values: list[Any]) -> bool:
    successes = sum(1 for value in values if is_time_like(value))
    return successes >= max(1, len(values) // 2 + 1)


def to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def is_time_like(value: Any) -> bool:
    return parse_time_like_label(value) is not None


def parse_time_like_label(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None

    normalized_candidate = candidate.replace("Z", "+00:00")
    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%Y-%m",
        "%Y/%m",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    )

    for date_format in formats:
        try:
            return datetime.strptime(candidate, date_format)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(normalized_candidate)
    except ValueError:
        return None


def format_label(value: str) -> str:
    return value.replace("_", " ").strip().title()
