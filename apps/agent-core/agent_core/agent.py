from __future__ import annotations

"""Main runtime orchestration for skill routing and tool execution."""

import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from opentelemetry import trace

from .llm_client import LLMClient, LLMClientError
from .mcp_client import MCPClient, MCPClientError
from .models import SkillDefinition
from .service_schema_client import ServiceSchemaClient, ServiceSchemaClientError
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
        service_schema_client: ServiceSchemaClient | None = None,
    ) -> None:
        self.settings = settings or AgentCoreSettings()
        self.skill_loader = skill_loader or SkillLoader(self.settings.SKILLS_DIR)
        self.mcp_client = mcp_client or MCPClient(self.settings)
        self.llm_client = llm_client or LLMClient(self.settings)
        self.service_schema_client = service_schema_client or ServiceSchemaClient(self.settings)

        self.skills: dict[str, SkillDefinition] = {}
        self.sessions: dict[str, AgentSession] = {}

        self._started = False
        self._schema_cache_data: dict[tuple[str, bool], dict[str, Any]] = {}
        self._schema_cache_at: dict[tuple[str, bool], float] = {}

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
        await self.service_schema_client.close()
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
        """Schema skill flow: refresh service-schema index and summarize relevant metadata."""
        with tracer.start_as_current_span("agent.skill.schema_analyzer") as span:
            await self._reindex_schema(include_indexes=False, session=session)
            schema_data = await self._search_schema(
                question=question,
                include_indexes=False,
                include_relationships=True,
                session=session,
            )
            tables = schema_data.get("ranked_tables", []) if isinstance(schema_data, dict) else []
            result = {
                "tables": tables,
                "rowCount": len(tables),
                "compact_context": schema_data.get("compact_context"),
                "suggested_relationships": schema_data.get("suggested_relationships", []),
            }
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
            schema_data = await self._search_schema(
                question=question,
                include_indexes=True,
                include_relationships=True,
                session=session,
            )
            schema_text = self._compact_schema_text(schema_data)

            with tracer.start_as_current_span("agent.generate_sql"):
                sql, params, _ = await self.llm_client.generate_sql(
                    question=question,
                    skill=skill,
                    schema_text=schema_text,
                    history=session.as_chat_context(self.settings.AGENT_HISTORY_LIMIT),
                    max_rows=max_rows,
                )

            query_data: dict[str, Any]
            retry_count = 0
            while True:
                # Always execute the current candidate SQL before deciding whether a retry is warranted.
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
                session.push_tool(
                    "postgres_query",
                    {"sql": sql, "params": params, "max_rows": max_rows},
                    self._summarize_result(query_data),
                )

                query_error = query_data.get("error") if isinstance(query_data, dict) else None
                if retry_count >= 1 or query_error not in {"db", "timeout"}:
                    break

                retry_count += 1
                # Feed the last failure back into SQL generation so the retry preserves intent
                # while avoiding the same DB/timeout failure mode.
                retry_message = query_data.get("message") if isinstance(query_data, dict) else None
                retry_reason = query_data.get("reason") if isinstance(query_data, dict) else None
                retry_code = query_data.get("code") if isinstance(query_data, dict) else None
                retry_context = (
                    f"{question}\n\n"
                    f"Previous SQL failed.\n"
                    f"previous_sql: {sql}\n"
                    f"error_type: {query_error}\n"
                    f"error_code: {retry_code}\n"
                    f"error_message: {retry_message or retry_reason or 'unknown'}\n"
                    "Rewrite SQL to preserve intent and avoid the same failure."
                )
                with tracer.start_as_current_span("agent.generate_sql_retry"):
                    sql, params, _ = await self.llm_client.generate_sql(
                        question=retry_context,
                        skill=skill,
                        schema_text=schema_text,
                        history=session.as_chat_context(self.settings.AGENT_HISTORY_LIMIT),
                        max_rows=max_rows,
                    )

            span.set_attribute("query.retry_count", retry_count)
            row_count = query_data.get("rowCount", 0) if isinstance(query_data, dict) else 0
            if isinstance(row_count, int):
                span.set_attribute("query.row_count", row_count)

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
            schema_data = await self._search_schema(
                question=question,
                include_indexes=True,
                include_relationships=True,
                session=session,
            )
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
            baseline_plan = self.extract_tool_data(explain_payload)
            session.push_tool(
                "postgres_explain",
                {"sql": sql, "params": params, "analyze": False},
                self._summarize_result(baseline_plan),
            )

            # Keep the original SQL as the default outcome and only replace it when the
            # rewrite path actually produces a different candidate plus a second plan.
            optimized_sql = sql
            optimized_params = params
            optimized_plan = baseline_plan
            optimization_reason = "no-rewrite"

            if not baseline_plan.get("error"):
                # Reuse the SQL generator with plan context so the skill can propose a
                # rewrite without adding a second specialized LLM prompt path.
                rewrite_context = (
                    f"{question}\n\n"
                    f"Current SQL:\n{sql}\n\n"
                    "Review the baseline EXPLAIN result and produce a safer/faster rewrite only if justified.\n"
                    f"Baseline EXPLAIN: {json.dumps(baseline_plan, ensure_ascii=False, default=str)}"
                )
                with tracer.start_as_current_span("agent.generate_sql_rewrite"):
                    candidate_sql, candidate_params, candidate_reason = await self.llm_client.generate_sql(
                        question=rewrite_context,
                        skill=skill,
                        schema_text=schema_text,
                        history=session.as_chat_context(self.settings.AGENT_HISTORY_LIMIT),
                        max_rows=max_rows,
                    )

                if candidate_sql.strip() != sql.strip() or candidate_params != params:
                    with tracer.start_as_current_span("agent.mcp.postgres_explain_rewrite"):
                        optimized_payload = await self.mcp_client.call_tool(
                            "postgres_explain",
                            {"sql": candidate_sql, "params": candidate_params, "analyze": False},
                        )
                    optimized_plan = self.extract_tool_data(optimized_payload)
                    session.push_tool(
                        "postgres_explain",
                        {"sql": candidate_sql, "params": candidate_params, "analyze": False},
                        self._summarize_result(optimized_plan),
                    )
                    optimized_sql = candidate_sql
                    optimized_params = candidate_params
                    optimization_reason = candidate_reason

            # Return both baseline and optimized views so callers can inspect the full tuning story.
            explain_data = {
                "baseline": {
                    "sql": sql,
                    "params": params,
                    "plan": baseline_plan,
                },
                "optimized": {
                    "sql": optimized_sql,
                    "params": optimized_params,
                    "plan": optimized_plan,
                    "reason": optimization_reason,
                    "changed": optimized_sql != sql or optimized_params != params,
                },
            }
            with tracer.start_as_current_span("agent.summarize_answer"):
                answer = await self.llm_client.summarize_answer(
                    question=question,
                    skill_name=skill.name,
                    sql=optimized_sql,
                    result=explain_data,
                )
            return {
                "question": question,
                "answer": answer,
                "sql": optimized_sql,
                "params": optimized_params,
                "result": explain_data,
            }

    async def _search_schema(
        self,
        *,
        question: str,
        include_indexes: bool,
        include_relationships: bool,
        session: AgentSession,
    ) -> dict[str, Any]:
        """Fetch compact schema context from service-schema with TTL cache."""
        with tracer.start_as_current_span("agent.schema_context") as span:
            now = time.time()
            cache_key = (question.strip().lower(), include_indexes)
            cached_data = self._schema_cache_data.get(cache_key)
            cached_at = self._schema_cache_at.get(cache_key, 0.0)
            cache_valid = (
                cached_data is not None
                and (now - cached_at) < self.settings.AGENT_SCHEMA_CACHE_TTL_SEC
            )
            span.set_attribute("schema.cache_hit", bool(cache_valid))
            span.set_attribute("schema.include_indexes", include_indexes)
            if cache_valid:
                return cached_data

            try:
                schema_data = await self.service_schema_client.search(
                    query=question,
                    max_tables=self.settings.SERVICE_SCHEMA_MAX_TABLES,
                    include_indexes=include_indexes,
                    include_relationships=include_relationships,
                )
            except ServiceSchemaClientError as exc:
                span.set_attribute("error", True)
                span.set_attribute("error.type", "ServiceSchemaClientError")
                raise AgentRuntimeError(f"Failed to retrieve schema from service-schema: {exc}") from exc

            session.push_tool(
                "service_schema.search",
                {
                    "query": question,
                    "max_tables": self.settings.SERVICE_SCHEMA_MAX_TABLES,
                    "include_indexes": include_indexes,
                    "include_relationships": include_relationships,
                },
                self._summarize_result(schema_data),
            )
            self._schema_cache_data[cache_key] = schema_data
            self._schema_cache_at[cache_key] = now
            return schema_data

    @staticmethod
    def _compact_schema_text(schema_data: dict[str, Any]) -> str:
        if not isinstance(schema_data, dict):
            return ""
        compact_context = schema_data.get("compact_context")
        if isinstance(compact_context, str):
            return compact_context
        return ""

    async def _reindex_schema(self, *, include_indexes: bool, session: AgentSession) -> dict[str, Any]:
        with tracer.start_as_current_span("agent.schema_reindex") as span:
            try:
                result = await self.service_schema_client.reindex(include_indexes=include_indexes)
            except ServiceSchemaClientError as exc:
                span.set_attribute("error", True)
                span.set_attribute("error.type", "ServiceSchemaClientError")
                raise AgentRuntimeError(f"Failed to reindex schema via service-schema: {exc}") from exc
            session.push_tool(
                "service_schema.reindex",
                {"include_indexes": include_indexes},
                self._summarize_result(result),
            )
            self._schema_cache_data.clear()
            self._schema_cache_at.clear()
            return result

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
        for key in ("rowCount", "durationMs", "duration_ms", "error", "reason", "message", "status", "version"):
            if key in payload:
                summary[key] = payload[key]
        if "tables" in payload and isinstance(payload["tables"], list):
            summary["tableCount"] = len(payload["tables"])
        if "ranked_tables" in payload and isinstance(payload["ranked_tables"], list):
            summary["tableCount"] = len(payload["ranked_tables"])
        if "compact_context" in payload and isinstance(payload["compact_context"], str):
            summary["contextChars"] = len(payload["compact_context"])
        if "plan" in payload:
            summary["hasPlan"] = True
        return summary

    def _get_session(self, session_id: str) -> AgentSession:
        """Return existing session or create a new one lazily."""
        # Evict before lookup so long-running workers do not retain idle sessions forever.
        self._evict_stale_sessions()
        existing = self.sessions.get(session_id)
        if existing:
            existing.touch()
            return existing
        session = AgentSession(session_id=session_id)
        self.sessions[session_id] = session
        self._evict_excess_sessions()
        return session

    def _evict_stale_sessions(self) -> None:
        ttl = self.settings.AGENT_SESSION_TTL_SEC
        if ttl <= 0 or not self.sessions:
            return

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl)
        stale_ids = [sid for sid, session in self.sessions.items() if session.last_touched < cutoff]
        for sid in stale_ids:
            self.sessions.pop(sid, None)

    def _evict_excess_sessions(self) -> None:
        max_sessions = self.settings.AGENT_MAX_SESSIONS
        if max_sessions <= 0 or len(self.sessions) <= max_sessions:
            return

        # Trim oldest sessions first so active conversations keep their accumulated context.
        overflow = len(self.sessions) - max_sessions
        oldest_sessions = sorted(self.sessions.items(), key=lambda item: item[1].last_touched)[:overflow]
        for sid, _ in oldest_sessions:
            self.sessions.pop(sid, None)
