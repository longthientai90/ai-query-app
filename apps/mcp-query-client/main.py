from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api_chat import router as chat_router
from api_tool import router as tool_router
from chat_service import ChatService
from mcp_service import MCPService


@asynccontextmanager
async def lifespan(app: FastAPI):
    mcp_service = MCPService()
    chat_service = ChatService()
    try:
        await mcp_service.start()
        app.state.mcp_service = mcp_service
        app.state.chat_service = chat_service
        yield
    finally:
        await mcp_service.stop()


app = FastAPI(title="mcp-query-client", lifespan=lifespan)
app.include_router(tool_router)
app.include_router(chat_router)
