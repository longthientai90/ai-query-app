import types

import asyncpg
import pytest

import tools.query as query_module
from config import Settings
from tools.query import register_query_tool


class FakePool:
    async def fetch(self, sql, *params):
        return [{"id": 1, "name": "alice"}]


class FakeTimeoutPool:
    async def fetch(self, sql, *params):
        raise asyncpg.QueryCanceledError("canceling statement due to statement timeout")


@pytest.mark.asyncio
async def test_postgres_query_returns_shape(monkeypatch, dummy_mcp, dummy_logger):
    settings = Settings(DATABASE_URL="postgresql://u:p@localhost:5432/db")
    register_query_tool(dummy_mcp, settings=settings, logger=dummy_logger)
    tool = dummy_mcp.tools["postgres_query"]

    monkeypatch.setattr(query_module, "get_pool", lambda: FakePool())
    result = await tool("SELECT id, name FROM users")

    assert result["rowCount"] == 1
    assert result["columns"] == ["id", "name"]
    assert result["rows"][0]["name"] == "alice"
    assert "durationMs" in result


@pytest.mark.asyncio
async def test_postgres_query_validation_error(dummy_mcp, dummy_logger):
    settings = Settings(DATABASE_URL="postgresql://u:p@localhost:5432/db")
    register_query_tool(dummy_mcp, settings=settings, logger=dummy_logger)
    tool = dummy_mcp.tools["postgres_query"]
    result = await tool("DELETE FROM users")
    assert result["error"] == "validation"


@pytest.mark.asyncio
async def test_postgres_query_timeout(monkeypatch, dummy_mcp, dummy_logger):
    settings = Settings(
        DATABASE_URL="postgresql://u:p@localhost:5432/db",
        DB_STATEMENT_TIMEOUT_MS=15000,
    )
    register_query_tool(dummy_mcp, settings=settings, logger=dummy_logger)
    tool = dummy_mcp.tools["postgres_query"]

    monkeypatch.setattr(query_module, "get_pool", lambda: FakeTimeoutPool())
    result = await tool("SELECT pg_sleep(30)")

    assert result["error"] == "timeout"
    assert result["timeoutMs"] == 15000
