from __future__ import annotations

from typing import Any

import asyncpg

from config import Settings
from db.pool import get_pool
from security.limiter import LimitExceededError, enforce_limit
from security.validator import SQLValidationError, validate_sql
from utils.logging import sql_hash
from utils.timing import timer


def register_query_tool(mcp, settings: Settings, logger, log_sql: bool = False) -> None:
    @mcp.tool()
    async def postgres_query(
        sql: str,
        params: list[Any] | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        async with timer() as t:
            try:
                logger.info("tool_query_request", tool="postgres_query", sql=sql, params=params, max_rows=max_rows)
                # 1) Validate SQL safety.
                validate_sql(sql)
                # 2) Enforce row cap by normalizing/injecting LIMIT.
                bounded_sql = enforce_limit(
                    sql=sql,
                    default_limit=settings.DEFAULT_LIMIT,
                    max_limit=settings.MAX_LIMIT,
                    max_rows=max_rows,
                )

                # 3) Execute read-only query and normalize asyncpg records to dict.
                rows = await get_pool().fetch(bounded_sql, *(params or []))
                dict_rows = [dict(row) for row in rows]
                columns = list(dict_rows[0].keys()) if dict_rows else []

                logger.info(
                    "tool_query_success",
                    tool="postgres_query",
                    sql_hash=sql_hash(sql),
                    rowCount=len(dict_rows),
                    durationMs=round(t.ms, 2),
                    sql=sql if log_sql else None,
                )
                return {
                    "rows": dict_rows,
                    "rowCount": len(dict_rows),
                    "columns": columns,
                    "durationMs": round(t.ms, 2),
                }
            except SQLValidationError as exc:
                return {"error": "validation", "reason": str(exc), "durationMs": round(t.ms, 2)}
            except LimitExceededError as exc:
                return {"error": "limit", "reason": str(exc), "durationMs": round(t.ms, 2)}
            except asyncpg.PostgresError as exc:
                logger.error(
                    "tool_query_db_error",
                    tool="postgres_query",
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
                    "tool_query_internal_error",
                    tool="postgres_query",
                    sql_hash=sql_hash(sql),
                    durationMs=round(t.ms, 2),
                )
                return {"error": "internal", "durationMs": round(t.ms, 2)}
