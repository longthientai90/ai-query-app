from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable

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
        self._reconnect_lock = asyncio.Lock()

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
            try:
                await self._stack.aclose()
            except Exception:
                # Connection can already be torn down when server restarts.
                pass
        self._stack = None
        self._session = None

    async def list_tools(self) -> dict[str, Any]:
        result = await self._with_reconnect(lambda: self.session.list_tools())
        return result.model_dump(by_alias=True, exclude_none=True)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._with_reconnect(
            lambda: self.session.call_tool(name, arguments=arguments)
        )
        payload = result.model_dump(by_alias=True, exclude_none=True)
        if result.isError:
            raise MCPServiceError(f"Tool call failed: {payload}")
        return payload

    async def _with_reconnect(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        try:
            return await operation()
        except Exception as exc:
            if not self._is_connection_error(exc):
                raise

        async with self._reconnect_lock:
            await self.stop()
            await self.start()
        return await operation()

    @staticmethod
    def _is_connection_error(exc: Exception) -> bool:
        message = str(exc).lower()
        keywords = (
            "connection reset",
            "forcibly closed",
            "server disconnected",
            "broken resource",
            "closed resource",
            "connection closed",
            "stream closed",
            "readerror",
            "connecterror",
            "session not found",
            "404",
            "not found",
        )
        return any(keyword in message for keyword in keywords) or isinstance(
            exc, (ConnectionError, ConnectionResetError, BrokenPipeError)
        )
