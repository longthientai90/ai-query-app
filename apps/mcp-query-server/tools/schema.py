from __future__ import annotations

from collections import defaultdict
from typing import Any

from opentelemetry import trace

from db.pool import get_pool
from utils.timing import timer

COLUMNS_SQL = """
SELECT
  c.table_name,
  c.column_name,
  c.data_type,
  c.is_nullable
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND ($1::text[] IS NULL OR c.table_name = ANY($1))
ORDER BY c.table_name, c.ordinal_position;
"""

PK_SQL = """
SELECT
  tc.table_name,
  kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND tc.table_schema = 'public';
"""

INDEX_SQL = """
SELECT
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND ($1::text[] IS NULL OR tablename = ANY($1));
"""

tracer = trace.get_tracer(__name__)


def register_schema_tool(mcp, logger) -> None:
    @mcp.tool()
    async def postgres_get_schema(
        tables: list[str] | None = None,
        include_indexes: bool = False,
    ) -> dict[str, Any]:
        async with timer() as t:
            with tracer.start_as_current_span("mcp.tool.postgres_get_schema") as span:
                span.set_attribute("db.system", "postgresql")
                span.set_attribute("db.operation", "schema")
                span.set_attribute("schema.include_indexes", include_indexes)
                try:
                    pool = get_pool()
                    table_filter = tables or None

                    # Fetch structural metadata from information_schema first.
                    with tracer.start_as_current_span("mcp.tool.schema.fetch_columns"):
                        column_rows = await pool.fetch(COLUMNS_SQL, table_filter)
                    with tracer.start_as_current_span("mcp.tool.schema.fetch_primary_keys"):
                        pk_rows = await pool.fetch(PK_SQL)

                    pk_map: dict[str, set[str]] = defaultdict(set)
                    for row in pk_rows:
                        pk_map[row["table_name"]].add(row["column_name"])

                    schema_map: dict[str, dict[str, Any]] = {}
                    for row in column_rows:
                        table_name = row["table_name"]
                        if table_name not in schema_map:
                            schema_map[table_name] = {"name": table_name, "columns": []}

                        schema_map[table_name]["columns"].append(
                            {
                                "name": row["column_name"],
                                "type": row["data_type"],
                                "nullable": row["is_nullable"] == "YES",
                                "pk": row["column_name"] in pk_map.get(table_name, set()),
                            }
                        )

                    if include_indexes:
                        # Index lookup is optional to keep default calls lightweight.
                        with tracer.start_as_current_span("mcp.tool.schema.fetch_indexes"):
                            index_rows = await pool.fetch(INDEX_SQL, table_filter)
                        index_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
                        for row in index_rows:
                            index_map[row["tablename"]].append(
                                {
                                    "name": row["indexname"],
                                    "definition": row["indexdef"],
                                }
                            )

                        for table_name, payload in schema_map.items():
                            payload["indexes"] = index_map.get(table_name, [])

                    result = {"tables": list(schema_map.values()), "durationMs": round(t.ms, 2)}
                    span.set_attribute("schema.table_count", len(result["tables"]))
                    logger.info(
                        "tool_schema_success",
                        tool="postgres_get_schema",
                        tableCount=len(result["tables"]),
                        durationMs=round(t.ms, 2),
                    )
                    return result
                except Exception:
                    span.set_attribute("error", True)
                    logger.exception("tool_schema_internal_error", tool="postgres_get_schema")
                    return {"error": "internal", "durationMs": round(t.ms, 2)}
