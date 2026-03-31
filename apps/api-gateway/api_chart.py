from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter

from schemas import ChartSuggestRequest, ChartSuggestResponse, ChartSuggestion

router = APIRouter(prefix="/api/chart", tags=["chart"])

MAX_SAMPLE_ROWS = 20


@router.post("/suggest", response_model=ChartSuggestResponse)
async def suggest_chart(payload: ChartSuggestRequest) -> ChartSuggestResponse:
    columns = [column for column in payload.columns if isinstance(column, str) and column.strip()]
    sample_rows = payload.rows[:MAX_SAMPLE_ROWS]
    analysis = analyze_columns(columns, sample_rows)

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

    if suggestions:
        summary = (
            f"Found {len(suggestions)} chart option(s) from the returned table based on column types and sample values."
        )
        return ChartSuggestResponse(can_chart=True, summary=summary, suggestions=suggestions)

    return ChartSuggestResponse(
        can_chart=False,
        summary="This table looks more like detailed records than chart-friendly grouped data.",
        suggestions=[],
    )


def analyze_columns(columns: list[str], rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    analysis: list[dict[str, str]] = []
    for column in columns:
        values = [row.get(column) for row in rows if isinstance(row, dict) and column in row]
        kind = infer_column_kind(column, values)
        analysis.append({"name": column, "kind": kind})
    return analysis


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
    if isinstance(value, datetime):
        return True
    if not isinstance(value, str):
        return False

    candidate = value.strip()
    if not candidate:
        return False

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
            datetime.strptime(candidate, date_format)
            return True
        except ValueError:
            continue

    try:
        datetime.fromisoformat(normalized_candidate)
        return True
    except ValueError:
        return False


def format_label(value: str) -> str:
    return value.replace("_", " ").strip().title()
