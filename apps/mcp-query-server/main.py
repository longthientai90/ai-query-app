from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from config import Settings
from db.pool import close_pool, init_pool
from tools import register_explain_tool, register_query_tool, register_schema_tool
from utils.logging import get_logger, setup_logging

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

settings = Settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger("mcp_query_server")


@asynccontextmanager
async def app_lifespan(_server):
    # Create pool in the same loop used by FastMCP request handlers.
    await init_pool(settings)
    logger.info("startup_complete", service="mcp-query-server")
    try:
        yield {}
    finally:
        await close_pool()
        logger.info("shutdown_complete", service="mcp-query-server")


# Single MCP app instance; tools are registered once at startup.
mcp = FastMCP("mcp-query-server", lifespan=app_lifespan)
register_query_tool(mcp, settings=settings, logger=logger, log_sql=settings.LOG_SQL)
register_schema_tool(mcp, logger=logger)
register_explain_tool(mcp, settings=settings, logger=logger, log_sql=settings.LOG_SQL)


def main() -> None:
    transport = settings.MCP_TRANSPORT.lower()
    if transport == "http":
        mcp.run(
            transport="http",
            host=settings.MCP_HOST,
            port=settings.MCP_PORT,
            path="/mcp",
            stateless_http=settings.MCP_STATELESS_HTTP,
        )
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
