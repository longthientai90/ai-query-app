from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openai import AsyncAzureOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict

from schemas import ChartSuggestion


class ChartLLMServiceError(RuntimeError):
    pass


class ChartLLMSettings(BaseSettings):
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    CHART_LLM_MAX_ROWS: int = 20

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ChartLLMService:
    def __init__(self, settings: ChartLLMSettings | None = None) -> None:
        self.settings = settings or ChartLLMSettings()
        self.client: AsyncAzureOpenAI | None = None

        if self.settings.AZURE_OPENAI_ENDPOINT and self.settings.AZURE_OPENAI_API_KEY and self.settings.AZURE_OPENAI_DEPLOYMENT:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
                api_key=self.settings.AZURE_OPENAI_API_KEY,
                api_version=self.settings.AZURE_OPENAI_API_VERSION,
            )

    @property
    def enabled(self) -> bool:
        return self.client is not None and bool(self.settings.AZURE_OPENAI_DEPLOYMENT)

    async def suggest_chart(
        self,
        *,
        question: str,
        columns: list[str],
        rows: list[dict[str, Any]],
        heuristic_suggestions: list[ChartSuggestion],
    ) -> tuple[bool, str, list[ChartSuggestion]]:
        if not self.enabled or self.client is None or not self.settings.AZURE_OPENAI_DEPLOYMENT:
            return bool(heuristic_suggestions), "LLM unavailable. Falling back to rule-based chart suggestions.", heuristic_suggestions

        sample_rows = rows[: self.settings.CHART_LLM_MAX_ROWS]
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a chart recommendation assistant. "
                    "Decide whether a SQL result table can be visualized as a bar or line chart. "
                    "Return JSON only with shape: "
                    '{"can_chart":true,"summary":"...","suggestions":[{"type":"bar","title":"...","reason":"...","x_column":"...","y_column":"..."}]}. '
                    "Allowed chart types: bar, line. "
                    "Prefer bar for category vs metric. Prefer line for time vs metric. "
                    "Do not suggest charts if the table is just detailed text records. "
                    "Use only columns that exist in the provided table."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"Columns: {json.dumps(columns, ensure_ascii=False)}\n"
                    f"Sample rows: {json.dumps(sample_rows, ensure_ascii=False, default=str)}\n"
                    f"Heuristic suggestions: {json.dumps([item.model_dump() for item in heuristic_suggestions], ensure_ascii=False)}"
                ),
            },
        ]

        completion = await self.client.chat.completions.create(
            model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0,
            max_completion_tokens=500,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content or "{}"
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ChartLLMServiceError(f"Azure OpenAI returned invalid JSON: {content}") from exc

        if not isinstance(payload, dict):
            raise ChartLLMServiceError("Azure OpenAI returned a non-object payload for chart suggestion")

        suggestions_payload = payload.get("suggestions")
        suggestions: list[ChartSuggestion] = []
        if isinstance(suggestions_payload, list):
            for item in suggestions_payload:
                if not isinstance(item, dict):
                    continue
                try:
                    suggestion = ChartSuggestion(**item)
                except Exception:
                    continue
                if suggestion.type in {"bar", "line"}:
                    suggestions.append(suggestion)

        can_chart = bool(payload.get("can_chart")) and bool(suggestions)
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            summary = "Azure OpenAI suggested chart options based on table semantics."

        if not suggestions and heuristic_suggestions:
            return True, "LLM returned no valid suggestions. Falling back to rule-based options.", heuristic_suggestions

        return can_chart, summary, suggestions
