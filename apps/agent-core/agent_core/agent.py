from __future__ import annotations

"""Main runtime orchestration for skill routing and tool execution."""

import json
import time
import uuid
from typing import Any

from opentelemetry import trace

from .llm_client import LLMClient, LLMClientError
from .mcp_client import MCPClient, MCPClientError
from .models import SkillDefinition
from .session import AgentSession
from .settings import AgentCoreSettings
from .skill_loader import SkillLoader, SkillLoaderError


class AgentRuntimeError(RuntimeError):
    pass


tracer = trace.get_tracer(__name__)


class Agent:
    """Coordinates skill selection, MCP tool calls, and response assembly."""

    def __init__(
        self,
        settings: AgentCoreSettings | None = None,
        *,
        skill_loader: SkillLoader | None = None,
        mcp_client: MCPClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.settings = settings or AgentCoreSettings()
        self.skill_loader = skill_loader or SkillLoader(self.settings.SKILLS_DIR)
        self.mcp_client = mcp_client or MCPClient(self.settings)
        self.llm_client = llm_client or LLMClient(self.settings)

        self.skills: dict[str, SkillDefinition] = {}
        self.sessions: dict[str, AgentSession] = {}

        self._started = False
        self._schema_cache_data: dict[str, Any] | None = None
        self._schema_cache_at = 0.0

    async def start(self) -> None:
        """Load skills once and establish MCP connection."""
        if self._started:
            return
        try:
            self.skills = self.skill_loader.load_skills()
        except SkillLoaderError as exc:
            raise AgentRuntimeError(f"Failed to load skills: {exc}") from exc

        try:
            await self.mcp_client.start()
        except MCPClientError as exc:
            raise AgentRuntimeError(f"Failed to start MCP client: {exc}") from exc

        self._started = True

    async def stop(self) -> None:
        """Gracefully close runtime resources."""
        await self.mcp_client.stop()
        self._started = False

    async def handle(
        self,
        *,
        question: str,
        max_rows: int | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Run one end-to-end request: route -> execute skill flow -> return answer."""
        with tracer.start_as_current_span("agent.handle") as span:
            span.set_attribute("question.length", len(question))
            if max_rows is not None:
                span.set_attribute("max_rows", max_rows)
            if session_id:
                span.set_attribute("session.id", session_id)

            if not self._started:
                await self.start()
            if not question.strip():
                span.set_attribute("error", True)
                raise AgentRuntimeError("Question cannot be empty")

            sid = session_id or str(uuid.uuid4())
            session = self._get_session(sid)
            session.push_user(question)

            skills = list(self.skills.values())
            with tracer.start_as_current_span("agent.route_skill"):
                # Route using LLM (or heuristic fallback if LLM is disabled).
                selected_skill, route_reason = await self.llm_client.route_skill(
                    question=question,
                    skills=skills,
                    history=session.as_chat_context(self.settings.AGENT_HISTORY_LIMIT),
                )
            skill = self.skills[selected_skill]
            span.set_attribute("skill.selected", skill.name)

            # Dispatch to skill-specific execution branch.
            if skill.name == "schema-analyzer":
                response = await self._run_schema_analyzer(
                    question=question,
                    session=session,
                    skill=skill,
                )
            elif skill.name == "performance-tuner":
                response = await self._run_performance_tuner(
                    question=question,
                    max_rows=max_rows,
                    session=session,
                    skill=skill,
                )
            else:
                response = await self._run_query_expert(
                    question=question,
                    max_rows=max_rows,
                    session=session,
                    skill=skill,
                )

            response["session_id"] = sid
            response["selected_skill"] = skill.name
            response["router_reason"] = route_reason
            session.push_assistant(response["answer"])
            session.trim(self.settings.AGENT_HISTORY_LIMIT)
            return response

    async def _run_schema_analyzer(
        self,
        *,
        question: str,
        session: AgentSession,
        skill: SkillDefinition,
    ) -> dict[str, Any]:
        """Schema skill flow: refresh schema and summarize structural metadata."""
        with tracer.start_as_current_span("agent.skill.schema_analyzer") as span:
            schema_data = await self._get_schema(force_refresh=True, session=session)
            tables = schema_data.get("tables", []) if isinstance(schema_data, dict) else []
            result = {"tables": tables, "rowCount": len(tables)}
            span.set_attribute("tables.count", len(tables))
            answer = await self.llm_client.summarize_answer(
                question=question,
                skill_name=skill.name,
                sql=None,
                result=result,
            )
            return {
                "question": question,
                "answer": answer,
                "sql": None,
                "params": [],
                "result": result,
            }

    async def _run_query_expert(
        self,
        *,
        question: str,
        max_rows: int | None,
        session: AgentSession,
        skill: SkillDefinition,
    ) -> dict[str, Any]:
        """Query skill flow: build SQL, execute query tool, and summarize rows."""
        with tracer.start_as_current_span("agent.skill.query_expert") as span:
            schema_data = await self._get_schema(force_refresh=False, session=session)
            schema_text = self._compact_schema_text(schema_data)

            with tracer.start_as_current_span("agent.generate_sql"):
                sql, params, _ = await self.llm_client.generate_sql(
                    question=question,
                    skill=skill,
                    schema_text=schema_text,
                    history=session.as_chat_context(self.settings.AGENT_HISTORY_LIMIT),
                    max_rows=max_rows,
                )

            with tracer.start_as_current_span("agent.mcp.postgres_query"):
                query_payload = await self.mcp_client.call_tool(
                    "postgres_query",
                    {
                        "sql": sql,
                        "params": params,
                        "max_rows": max_rows,
                    },
                )
            query_data = self.extract_tool_data(query_payload)
            row_count = query_data.get("rowCount", 0) if isinstance(query_data, dict) else 0
            if isinstance(row_count, int):
                span.set_attribute("query.row_count", row_count)
            session.push_tool(
                "postgres_query",
                {"sql": sql, "params": params, "max_rows": max_rows},
                self._summarize_result(query_data),
            )

            with tracer.start_as_current_span("agent.summarize_answer"):
                answer = await self.llm_client.summarize_answer(
                    question=question,
                    skill_name=skill.name,
                    sql=sql,
                    result=query_data,
                )
            return {
                "question": question,
                "answer": answer,
                "sql": sql,
                "params": params,
                "result": query_data,
            }

    async def _run_performance_tuner(
        self,
        *,
        question: str,
        max_rows: int | None,
        session: AgentSession,
        skill: SkillDefinition,
    ) -> dict[str, Any]:
        """Performance skill flow: build SQL candidate and inspect its EXPLAIN plan."""
        with tracer.start_as_current_span("agent.skill.performance_tuner"):
            schema_data = await self._get_schema(force_refresh=False, session=session)
            schema_text = self._compact_schema_text(schema_data)

            with tracer.start_as_current_span("agent.generate_sql"):
                sql, params, _ = await self.llm_client.generate_sql(
                    question=question,
                    skill=skill,
                    schema_text=schema_text,
                    history=session.as_chat_context(self.settings.AGENT_HISTORY_LIMIT),
                    max_rows=max_rows,
                )
            with tracer.start_as_current_span("agent.mcp.postgres_explain"):
                explain_payload = await self.mcp_client.call_tool(
                    "postgres_explain",
                    {"sql": sql, "params": params, "analyze": False},
                )
            explain_data = self.extract_tool_data(explain_payload)
            session.push_tool(
                "postgres_explain",
                {"sql": sql, "params": params, "analyze": False},
                self._summarize_result(explain_data),
            )
            with tracer.start_as_current_span("agent.summarize_answer"):
                answer = await self.llm_client.summarize_answer(
                    question=question,
                    skill_name=skill.name,
                    sql=sql,
                    result=explain_data,
                )
            return {
                "question": question,
                "answer": answer,
                "sql": sql,
                "params": params,
                "result": explain_data,
            }

    async def _get_schema(self, *, force_refresh: bool, session: AgentSession) -> dict[str, Any]:
        """Fetch schema with TTL cache to avoid repeated metadata calls."""
        with tracer.start_as_current_span("agent.schema_context") as span:
            now = time.time()
            cache_valid = (
                not force_refresh
                and self._schema_cache_data is not None
                and (now - self._schema_cache_at) < self.settings.AGENT_SCHEMA_CACHE_TTL_SEC
            )
            span.set_attribute("schema.cache_hit", bool(cache_valid))
            if cache_valid:
                return self._schema_cache_data

            payload = await self.mcp_client.call_tool(
                "postgres_get_schema",
                {"tables": None, "include_indexes": False},
            )
            schema_data = self.extract_tool_data(payload)
            session.push_tool(
                "postgres_get_schema",
                {"tables": None, "include_indexes": False},
                self._summarize_result(schema_data),
            )
            self._schema_cache_data = schema_data
            self._schema_cache_at = now
            return schema_data

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

    @staticmethod
    def extract_tool_data(payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize MCP tool response envelopes into a plain dict payload."""
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

    @staticmethod
    def _summarize_result(payload: dict[str, Any]) -> dict[str, Any]:
        """Store lightweight tool event metadata for session traceability."""
        if not isinstance(payload, dict):
            return {"type": type(payload).__name__}
        summary: dict[str, Any] = {}
        for key in ("rowCount", "durationMs", "error", "reason", "message"):
            if key in payload:
                summary[key] = payload[key]
        if "tables" in payload and isinstance(payload["tables"], list):
            summary["tableCount"] = len(payload["tables"])
        if "plan" in payload:
            summary["hasPlan"] = True
        return summary

    def _get_session(self, session_id: str) -> AgentSession:
        """Return existing session or create a new one lazily."""
        existing = self.sessions.get(session_id)
        if existing:
            return existing
        session = AgentSession(session_id=session_id)
        self.sessions[session_id] = session
        return session
