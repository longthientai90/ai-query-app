from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServiceError(RuntimeError):
    pass


class MCPClientSettings(BaseSettings):
    MCP_SERVER_URL: str = "http://127.0.0.1:8000/mcp"
    MCP_SERVER_TRANSPORT: str = "http"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class MCPService:
    def __init__(self, settings: MCPClientSettings | None = None) -> None:
        self.settings = settings or MCPClientSettings()
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise MCPServiceError("MCP session is not initialized")
        return self._session

    async def start(self) -> None:
        if self._session is not None:
            return

        transport = self.settings.MCP_SERVER_TRANSPORT.lower()
        if transport != "http":
            raise MCPServiceError("Only MCP_SERVER_TRANSPORT=http is supported")

        stack = AsyncExitStack()
        read_stream, write_stream, _ = await stack.enter_async_context(
            streamablehttp_client(self.settings.MCP_SERVER_URL)
        )
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()

        self._stack = stack
        self._session = session

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    async def list_tools(self) -> dict[str, Any]:
        result = await self.session.list_tools()
        return result.model_dump(by_alias=True, exclude_none=True)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self.session.call_tool(name, arguments=arguments)
        payload = result.model_dump(by_alias=True, exclude_none=True)
        if result.isError:
            raise MCPServiceError(f"Tool call failed: {payload}")
        return payload
