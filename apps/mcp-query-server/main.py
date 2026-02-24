from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from config import Settings
from db.pool import close_pool, init_pool
from tools import register_explain_tool, register_query_tool, register_schema_tool
from utils.logging import get_logger, setup_logging

settings = Settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger("mcp_query_server")

# Single MCP app instance; tools are registered once at startup.
mcp = FastMCP("mcp-query-server")
register_query_tool(mcp, settings=settings, logger=logger, log_sql=settings.LOG_SQL)
register_schema_tool(mcp, logger=logger)
register_explain_tool(mcp, settings=settings, logger=logger, log_sql=settings.LOG_SQL)


async def _startup() -> None:
    await init_pool(settings)
    logger.info("startup_complete", service="mcp-query-server")


async def _shutdown() -> None:
    await close_pool()
    logger.info("shutdown_complete", service="mcp-query-server")


def main() -> None:
    # Open DB resources before serving MCP requests.
    asyncio.run(_startup())
    try:
        mcp.run(transport="http", host=settings.MCP_HOST, port=settings.MCP_PORT)
    finally:
        # Always release DB resources when server stops.
        asyncio.run(_shutdown())


if __name__ == "__main__":
    main()
