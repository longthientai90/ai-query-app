from __future__ import annotations

import json
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ChatService:
    def __init__(self, settings: AzureOpenAISettings | None = None) -> None:
        self.settings = settings or AzureOpenAISettings()
        self.client = AsyncAzureOpenAI(
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            api_version=self.settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
        )

    async def ask(self, mcp_service: MCPService, question: str, max_rows: int | None) -> dict[str, Any]:
        schema_payload = await mcp_service.call_tool(
            "postgres_get_schema",
            {"tables": None, "include_indexes": False},
        )
        schema_data = self.extract_tool_data(schema_payload)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a PostgreSQL SQL generator. "
                    "Return only valid JSON with shape: "
                    '{"sql":"...","params":[]}. '
                    "Rules: query must be read-only SELECT or WITH...SELECT, no comments, no semicolons."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Database schema:\n{json.dumps(schema_data, ensure_ascii=True)}"
                ),
            },
        ]

        completion = await self.client.chat.completions.create(
            model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0,
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
        user_json = await self._build_user_json(question=question, rows=rows)

        return {
            "question": question,
            "sql": sql,
            "params": params,
            "result": query_data,
            "answer": user_json,
        }

    async def _build_user_json(self, question: str, rows: list[Any]) -> dict[str, Any]:
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
                    f"Rows JSON: {json.dumps(rows, ensure_ascii=True)}"
                ),
            },
        ]
        completion = await self.client.chat.completions.create(
            model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ChatServiceError("Azure OpenAI did not return a JSON object for answer")
        return parsed

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
