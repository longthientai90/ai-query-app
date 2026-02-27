import asyncpg
import pytest

import tools.explain as explain_module
from config import Settings
from tools.explain import register_explain_tool


class FakeTx:
    async def start(self):
        return None

    async def rollback(self):
        return None


class FakeConn:
    def transaction(self):
        return FakeTx()

    async def fetch(self, sql, *params):
        return [[{"Plan": {"Node Type": "Seq Scan"}}]]


class FakeConnTimeout:
    def transaction(self):
        return FakeTx()

    async def fetch(self, sql, *params):
        raise asyncpg.QueryCanceledError("canceling statement due to statement timeout")


class _AcquireContext:
    async def __aenter__(self):
        return FakeConn()

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakePool:
    def acquire(self):
        return _AcquireContext()


class _AcquireContextTimeout:
    async def __aenter__(self):
        return FakeConnTimeout()

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeTimeoutPool:
    def acquire(self):
        return _AcquireContextTimeout()


@pytest.mark.asyncio
async def test_postgres_explain(monkeypatch, dummy_mcp, dummy_logger):
    settings = Settings(DATABASE_URL="postgresql://u:p@localhost:5432/db")
    register_explain_tool(dummy_mcp, settings=settings, logger=dummy_logger)
    tool = dummy_mcp.tools["postgres_explain"]
    monkeypatch.setattr(explain_module, "get_pool", lambda: FakePool())

    result = await tool("SELECT * FROM users", analyze=True)
    assert "plan" in result
    assert "durationMs" in result


@pytest.mark.asyncio
async def test_postgres_explain_timeout(monkeypatch, dummy_mcp, dummy_logger):
    settings = Settings(
        DATABASE_URL="postgresql://u:p@localhost:5432/db",
        DB_STATEMENT_TIMEOUT_MS=15000,
    )
    register_explain_tool(dummy_mcp, settings=settings, logger=dummy_logger)
    tool = dummy_mcp.tools["postgres_explain"]
    monkeypatch.setattr(explain_module, "get_pool", lambda: FakeTimeoutPool())

    result = await tool("SELECT pg_sleep(30)", analyze=True)
    assert result["error"] == "timeout"
    assert result["timeoutMs"] == 15000
