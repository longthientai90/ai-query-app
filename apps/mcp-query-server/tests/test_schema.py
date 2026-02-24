import pytest

import tools.schema as schema_module
from tools.schema import register_schema_tool


class FakePool:
    async def fetch(self, sql, *params):
        if "information_schema.columns" in sql:
            return [
                {
                    "table_name": "users",
                    "column_name": "id",
                    "data_type": "integer",
                    "is_nullable": "NO",
                },
                {
                    "table_name": "users",
                    "column_name": "name",
                    "data_type": "text",
                    "is_nullable": "YES",
                },
            ]
        if "table_constraints" in sql:
            return [{"table_name": "users", "column_name": "id"}]
        if "pg_indexes" in sql:
            return [{"tablename": "users", "indexname": "users_pkey", "indexdef": "CREATE UNIQUE INDEX ..."}]
        return []


@pytest.mark.asyncio
async def test_postgres_get_schema(monkeypatch, dummy_mcp, dummy_logger):
    register_schema_tool(dummy_mcp, logger=dummy_logger)
    tool = dummy_mcp.tools["postgres_get_schema"]
    monkeypatch.setattr(schema_module, "get_pool", lambda: FakePool())

    result = await tool(include_indexes=True)
    assert len(result["tables"]) == 1
    assert result["tables"][0]["name"] == "users"
    assert result["tables"][0]["columns"][0]["pk"] is True
    assert result["tables"][0]["indexes"][0]["name"] == "users_pkey"

