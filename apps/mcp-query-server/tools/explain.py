from __future__ import annotations

from typing import Any

import asyncpg

from config import Settings
from db.pool import get_pool
from security.limiter import enforce_limit
from security.validator import SQLValidationError, validate_sql
from utils.logging import sql_hash
from utils.timing import timer


def register_explain_tool(mcp, settings: Settings, logger, log_sql: bool = False) -> None:
    @mcp.tool()
    async def postgres_explain(
        sql: str,
        params: list[Any] | None = None,
        analyze: bool = False,
    ) -> dict[str, Any]:
        async with timer() as t:
            try:
                # Reuse the same read-only safety checks as normal query execution.
                validate_sql(sql)
                bounded_sql = enforce_limit(
                    sql=sql,
                    default_limit=settings.DEFAULT_LIMIT,
                    max_limit=settings.MAX_LIMIT,
                )
                explain_prefix = "EXPLAIN (FORMAT JSON, ANALYZE TRUE)" if analyze else "EXPLAIN (FORMAT JSON)"
                explain_sql = f"{explain_prefix} {bounded_sql}"

                pool = get_pool()
                async with pool.acquire() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        # EXPLAIN ANALYZE can run the query; rollback protects against side effects.
                        rows = await conn.fetch(explain_sql, *(params or []))
                    finally:
                        await tx.rollback()

                plan = rows[0][0] if rows else []
                logger.info(
                    "tool_explain_success",
                    tool="postgres_explain",
                    sql_hash=sql_hash(sql),
                    durationMs=round(t.ms, 2),
                    sql=sql if log_sql else None,
                )
                return {"plan": plan, "durationMs": round(t.ms, 2)}
            except SQLValidationError as exc:
                return {"error": "validation", "reason": str(exc), "durationMs": round(t.ms, 2)}
            except asyncpg.PostgresError as exc:
                logger.error(
                    "tool_explain_db_error",
                    tool="postgres_explain",
                    sql_hash=sql_hash(sql),
                    durationMs=round(t.ms, 2),
                    error=str(exc),
                )
                return {
                    "error": "db",
                    "message": str(exc),
                    "code": getattr(exc, "sqlstate", None),
                    "durationMs": round(t.ms, 2),
                }
            except Exception:
                logger.exception(
                    "tool_explain_internal_error",
                    tool="postgres_explain",
                    sql_hash=sql_hash(sql),
                    durationMs=round(t.ms, 2),
                )
                return {"error": "internal", "durationMs": round(t.ms, 2)}
