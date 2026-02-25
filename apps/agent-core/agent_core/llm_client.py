from __future__ import annotations

"""LLM wrapper for routing, SQL generation, and answer summarization."""

import json
import re
from typing import Any

from openai import AsyncAzureOpenAI, AsyncOpenAI

from .models import SkillDefinition
from .settings import AgentCoreSettings


class LLMClientError(RuntimeError):
    pass


class LLMClient:
    """Provides one abstraction layer over OpenAI/Azure chat completions."""

    def __init__(self, settings: AgentCoreSettings) -> None:
        self.settings = settings
        self.provider = settings.LLM_PROVIDER.lower()
        self.client: AsyncOpenAI | AsyncAzureOpenAI | None = None
        self.model: str | None = None

        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise LLMClientError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
            self.model = settings.OPENAI_MODEL
        elif self.provider == "azure":
            if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_API_KEY:
                raise LLMClientError(
                    "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are required when LLM_PROVIDER=azure"
                )
            if not settings.AZURE_OPENAI_DEPLOYMENT:
                raise LLMClientError("AZURE_OPENAI_DEPLOYMENT is required when LLM_PROVIDER=azure")
            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
            self.model = settings.AZURE_OPENAI_DEPLOYMENT
        elif self.provider == "none":
            self.client = None
            self.model = None
        else:
            raise LLMClientError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")

    @property
    def enabled(self) -> bool:
        """True when a real LLM backend is configured and ready."""
        return self.client is not None and self.model is not None

    async def route_skill(
        self,
        *,
        question: str,
        skills: list[SkillDefinition],
        history: list[dict[str, str]],
    ) -> tuple[str, str]:
        """Pick the best skill for the request using LLM, with heuristic fallback."""
        if not skills:
            raise LLMClientError("No skills loaded")

        if not self.enabled:
            picked = self._heuristic_route(question, skills)
            return picked, "heuristic-router"

        available_skills = "\n".join(
            f"- {skill.name}: {skill.description}"
            for skill in skills
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict router. Choose exactly one skill for the user question. "
                    "Respond as JSON with shape: {\"skill\":\"...\",\"reason\":\"...\"}."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"<available_skills>\n{available_skills}\n</available_skills>\n\n"
                    f"<conversation_history>\n{json.dumps(history, ensure_ascii=True)}\n</conversation_history>\n\n"
                    f"<user_question>{question}</user_question>"
                ),
            },
        ]
        parsed = await self._chat_json(messages=messages, max_tokens=220)
        skill = parsed.get("skill")
        reason = parsed.get("reason", "")
        names = {item.name for item in skills}
        if isinstance(skill, str) and skill in names:
            return skill, reason if isinstance(reason, str) else "llm-router"

        picked = self._heuristic_route(question, skills)
        return picked, "llm-router-fallback"

    async def generate_sql(
        self,
        *,
        question: str,
        skill: SkillDefinition,
        schema_text: str,
        history: list[dict[str, str]],
        max_rows: int | None,
    ) -> tuple[str, list[Any], str]:
        """Generate read-only SQL and params for the selected skill context."""
        if not self.enabled:
            return self._heuristic_sql(question=question, schema_text=schema_text, max_rows=max_rows)

        messages = [
            {
                "role": "system",
                "content": (
                    f"{skill.instructions}\n\n"
                    "Output JSON only with shape: {\"sql\":\"...\",\"params\":[],\"reason\":\"...\"}. "
                    "Constraints: read-only SQL only (SELECT or WITH...SELECT), no semicolons, no comments."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"max_rows hint: {max_rows if max_rows is not None else 'null'}\n\n"
                    f"Schema:\n{schema_text}\n\n"
                    f"Conversation history: {json.dumps(history, ensure_ascii=True)}"
                ),
            },
        ]
        payload = await self._chat_json(messages=messages, max_tokens=600)
        sql = payload.get("sql")
        params = payload.get("params") or []
        reason = payload.get("reason", "")

        if not isinstance(sql, str) or not sql.strip():
            raise LLMClientError("LLM did not return SQL text")
        if not isinstance(params, list):
            raise LLMClientError("LLM returned non-list SQL params")

        cleaned_sql = sql.strip().rstrip(";")
        return cleaned_sql, params, reason if isinstance(reason, str) else "llm-sql"

    async def summarize_answer(
        self,
        *,
        question: str,
        skill_name: str,
        sql: str | None,
        result: dict[str, Any],
    ) -> str:
        """Turn raw tool output into a concise user-facing answer."""
        rows = result.get("rows") if isinstance(result, dict) else None
        row_count = result.get("rowCount") if isinstance(result, dict) else None
        if not isinstance(rows, list):
            rows = []
        if not isinstance(row_count, int):
            row_count = len(rows)

        if not self.enabled:
            return self._heuristic_summary(question=question, skill_name=skill_name, rows=rows, row_count=row_count)

        compact_rows = self._compact_rows(rows, max_rows=12, max_chars=self.settings.AGENT_MAX_VALUE_CHARS)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a data assistant. Provide a concise and accurate final answer to the user question. "
                    "Do not invent values that are not present in data."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Skill: {skill_name}\n"
                    f"Question: {question}\n"
                    f"SQL: {sql or '(none)'}\n"
                    f"Row count: {row_count}\n"
                    f"Rows preview: {json.dumps(compact_rows, ensure_ascii=True)}"
                ),
            },
        ]
        return (await self._chat_text(messages=messages, max_tokens=400)).strip()

    def _heuristic_route(self, question: str, skills: list[SkillDefinition]) -> str:
        """Rule-based routing used when LLM is disabled or router output is invalid."""
        text = question.lower()
        names = {skill.name for skill in skills}

        schema_keywords = ("schema", "cau truc", "cấu trúc", "table", "column", "bang", "bảng")
        perf_keywords = ("explain", "performance", "toi uu", "tối ưu", "cham", "chậm", "index", "join")

        if any(word in text for word in schema_keywords) and "schema-analyzer" in names:
            return "schema-analyzer"
        if any(word in text for word in perf_keywords) and "performance-tuner" in names:
            return "performance-tuner"
        if "query-expert" in names:
            return "query-expert"
        return skills[0].name

    def _heuristic_sql(self, *, question: str, schema_text: str, max_rows: int | None) -> tuple[str, list[Any], str]:
        """Minimal SQL fallback so local development can run without an LLM key."""
        safe_limit = max_rows if isinstance(max_rows, int) and max_rows > 0 else self.settings.AGENT_DEFAULT_MAX_ROWS
        question_lower = question.lower()

        if "doanh thu" in question_lower or "revenue" in question_lower:
            return (
                "SELECT date_trunc('month', created_at) AS month, "
                "SUM(total_amount) AS revenue "
                "FROM orders "
                "WHERE date_trunc('month', created_at) = date_trunc('month', CURRENT_DATE) "
                "GROUP BY 1 "
                "ORDER BY 1 DESC "
                f"LIMIT {safe_limit}",
                [],
                "heuristic-revenue-sql",
            )

        table_name = self._first_table_from_schema(schema_text) or "orders"
        return (f"SELECT * FROM {table_name} LIMIT {safe_limit}", [], "heuristic-generic-sql")

    @staticmethod
    def _first_table_from_schema(schema_text: str) -> str | None:
        match = re.search(r"^([a-zA-Z_][\w]*)\s*\(", schema_text, flags=re.MULTILINE)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _heuristic_summary(*, question: str, skill_name: str, rows: list[Any], row_count: int) -> str:
        if skill_name == "schema-analyzer":
            return f"Da phan tich schema. Tong so bang tim thay: {row_count}."
        if skill_name == "performance-tuner":
            return "Da phan tich EXPLAIN plan. Vui long xem chi tiet trong truong 'result'."
        if row_count == 0:
            return "Khong tim thay du lieu phu hop voi cau hoi."
        return f"Da tim thay {row_count} dong du lieu cho cau hoi: {question}"

    async def _chat_json(self, *, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        """Force JSON mode and parse into a dict."""
        content = await self._chat_text(messages=messages, max_tokens=max_tokens, json_mode=True)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"LLM did not return valid JSON: {content}") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("LLM JSON response must be an object")
        return parsed

    async def _chat_text(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        json_mode: bool = False,
    ) -> str:
        """Shared chat completion call used by all LLM interactions."""
        if not self.enabled or self.client is None or self.model is None:
            raise LLMClientError("LLM client is disabled")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_completion_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        completion = await self.client.chat.completions.create(**kwargs)
        content = completion.choices[0].message.content
        if not content:
            raise LLMClientError("LLM returned empty response")
        return content

    @staticmethod
    def _compact_rows(rows: list[Any], *, max_rows: int, max_chars: int) -> list[Any]:
        compacted: list[Any] = []
        for row in rows[:max_rows]:
            if not isinstance(row, dict):
                compacted.append(row)
                continue
            compact_row: dict[str, Any] = {}
            for key, value in row.items():
                if isinstance(value, str) and len(value) > max_chars:
                    compact_row[key] = value[: max_chars - 3] + "..."
                else:
                    compact_row[key] = value
            compacted.append(compact_row)
        return compacted
