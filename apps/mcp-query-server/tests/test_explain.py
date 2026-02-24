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


class _AcquireContext:
    async def __aenter__(self):
        return FakeConn()

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakePool:
    def acquire(self):
        return _AcquireContext()


@pytest.mark.asyncio
async def test_postgres_explain(monkeypatch, dummy_mcp, dummy_logger):
    settings = Settings(DATABASE_URL="postgresql://u:p@localhost:5432/db")
    register_explain_tool(dummy_mcp, settings=settings, logger=dummy_logger)
    tool = dummy_mcp.tools["postgres_explain"]
    monkeypatch.setattr(explain_module, "get_pool", lambda: FakePool())

    result = await tool("SELECT * FROM users", analyze=True)
    assert "plan" in result
    assert "durationMs" in result

