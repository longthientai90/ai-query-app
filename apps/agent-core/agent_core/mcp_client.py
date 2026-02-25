from __future__ import annotations

"""Resilient MCP client with automatic reconnect on transient connection errors."""

import asyncio
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .settings import AgentCoreSettings


class MCPClientError(RuntimeError):
    pass


class MCPClient:
    """Small wrapper around MCP `ClientSession` for tool discovery and calls."""

    def __init__(self, settings: AgentCoreSettings) -> None:
        self.settings = settings
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._reconnect_lock = asyncio.Lock()

    @property
    def session(self) -> ClientSession:
        """Return active session or fail fast if lifecycle has not started."""
        if self._session is None:
            raise MCPClientError("MCP session is not initialized")
        return self._session

    async def start(self) -> None:
        """Open streamable HTTP transport and initialize MCP session."""
        if self._session is not None:
            return
        if self.settings.MCP_SERVER_TRANSPORT.lower() != "http":
            raise MCPClientError("Only MCP_SERVER_TRANSPORT=http is supported")

        stack = AsyncExitStack()
        read_stream, write_stream, _ = await stack.enter_async_context(
            streamablehttp_client(self.settings.MCP_SERVER_URL)
        )
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()

        self._stack = stack
        self._session = session

    async def stop(self) -> None:
        """Close all opened async contexts and clear client state."""
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except Exception:
                pass
        self._stack = None
        self._session = None

    async def list_tools(self) -> dict[str, Any]:
        """Return MCP server tool catalog as a plain dict."""
        result = await self._with_reconnect(lambda: self.session.list_tools())
        return result.model_dump(by_alias=True, exclude_none=True)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute one tool call and surface MCP error payloads as exceptions."""
        result = await self._with_reconnect(lambda: self.session.call_tool(name, arguments=arguments))
        payload = result.model_dump(by_alias=True, exclude_none=True)
        if result.isError:
            raise MCPClientError(f"Tool call failed: {payload}")
        return payload

    async def _with_reconnect(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """Retry once after reconnect if a connection-level failure is detected."""
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
