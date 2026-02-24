from __future__ import annotations

import json
import time
from typing import Any

from openai import AsyncAzureOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict

from mcp_service import MCPService


class ChatServiceError(RuntimeError):
    pass


class AzureOpenAISettings(BaseSettings):
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    AZURE_OPENAI_DEPLOYMENT: str
    CHAT_SQL_MAX_TOKENS: int = 300
    CHAT_ANSWER_MAX_TOKENS: int = 500
    CHAT_SCHEMA_CACHE_TTL_SEC: int = 300
    CHAT_MAX_ROWS_TO_AI: int = 20
    CHAT_MAX_VALUE_CHARS: int = 200

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ChatService:
    def __init__(self, settings: AzureOpenAISettings | None = None) -> None:
        self.settings = settings or AzureOpenAISettings()
        self.client = AsyncAzureOpenAI(
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            api_version=self.settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
        )
        self._schema_cache_text: str | None = None
        self._schema_cache_at: float = 0.0

    async def ask(self, mcp_service: MCPService, question: str, max_rows: int | None) -> dict[str, Any]:
        schema_text = await self._get_schema_text(mcp_service)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a PostgreSQL SQL generator. "
                    "Return only valid JSON with shape: "
                    '{"sql":"...","params":[]}. '
                    "Rules: query must be read-only SELECT or WITH...SELECT, no comments, no semicolons. "
                    "Prefer selecting only needed columns."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Database schema (compact):\n{schema_text}"
                ),
            },
        ]

        completion = await self.client.chat.completions.create(
            model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0,
            max_completion_tokens=self.settings.CHAT_SQL_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        generated = json.loads(content)
        sql = generated.get("sql")
        params = generated.get("params") or []

        if not isinstance(sql, str) or not sql.strip():
            raise ChatServiceError("Azure OpenAI did not return valid SQL")
        if not isinstance(params, list):
            raise ChatServiceError("Azure OpenAI returned invalid params")

        query_payload = await mcp_service.call_tool(
            "postgres_query",
            {"sql": sql, "params": params, "max_rows": max_rows},
        )
        query_data = self.extract_tool_data(query_payload)
        rows = query_data.get("rows", []) if isinstance(query_data, dict) else []
        user_json = await self._build_user_json(
            question=question,
            rows=rows,
            total_row_count=int(query_data.get("rowCount", len(rows))) if isinstance(query_data, dict) else len(rows),
        )

        return {
            "question": question,
            "sql": sql,
            "params": params,
            "result": query_data,
            "answer": user_json,
        }

    async def _build_user_json(self, question: str, rows: list[Any], total_row_count: int) -> dict[str, Any]:
        preview_rows = self._compact_rows(rows)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a data response formatter. "
                    "Return only valid JSON object with fields: "
                    '{"summary":"...","rowCount":0,"items":[...]} '
                    "The items must come from the provided rows only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"Total row count: {total_row_count}\n"
                    f"Rows preview JSON: {json.dumps(preview_rows, ensure_ascii=True)}"
                ),
            },
        ]
        completion = await self.client.chat.completions.create(
            model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0,
            max_completion_tokens=self.settings.CHAT_ANSWER_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ChatServiceError("Azure OpenAI did not return a JSON object for answer")
        return parsed

    async def _get_schema_text(self, mcp_service: MCPService) -> str:
        now = time.time()
        if (
            self._schema_cache_text is not None
            and now - self._schema_cache_at < self.settings.CHAT_SCHEMA_CACHE_TTL_SEC
        ):
            return self._schema_cache_text

        schema_payload = await mcp_service.call_tool(
            "postgres_get_schema",
            {"tables": None, "include_indexes": False},
        )
        schema_data = self.extract_tool_data(schema_payload)
        schema_text = self._compact_schema_text(schema_data)
        self._schema_cache_text = schema_text
        self._schema_cache_at = now
        return schema_text

    @staticmethod
    def _compact_schema_text(schema_data: dict[str, Any]) -> str:
        tables = schema_data.get("tables", []) if isinstance(schema_data, dict) else []
        lines: list[str] = []
        for table in tables:
            table_name = table.get("name")
            columns = table.get("columns", [])
            if not isinstance(table_name, str) or not isinstance(columns, list):
                continue
            col_parts: list[str] = []
            for col in columns:
                col_name = col.get("name")
                col_type = col.get("type")
                if isinstance(col_name, str) and isinstance(col_type, str):
                    col_parts.append(f"{col_name}:{col_type}")
            lines.append(f"{table_name}({', '.join(col_parts)})")
        return "\n".join(lines)

    def _compact_rows(self, rows: list[Any]) -> list[Any]:
        limit = self.settings.CHAT_MAX_ROWS_TO_AI
        max_chars = self.settings.CHAT_MAX_VALUE_CHARS
        compacted: list[Any] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                compacted.append(row)
                continue
            new_row: dict[str, Any] = {}
            for key, value in row.items():
                if isinstance(value, str) and len(value) > max_chars:
                    new_row[key] = value[: max_chars - 3] + "..."
                else:
                    new_row[key] = value
            compacted.append(new_row)
        return compacted

    @staticmethod
    def extract_tool_data(payload: dict[str, Any]) -> dict[str, Any]:
        if "structuredContent" in payload and isinstance(payload["structuredContent"], dict):
            return payload["structuredContent"]

        content = payload.get("content")
        if isinstance(content, list) and content:
            for item in content:
                if isinstance(item, dict):
                    if "json" in item and isinstance(item["json"], dict):
                        return item["json"]
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        try:
                            parsed = json.loads(item["text"])
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            pass
        return payload
