from __future__ import annotations

import asyncio
import json
import shlex
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Awaitable, Callable

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChartMCPServiceError(RuntimeError):
    pass


class ChartMCPSettings(BaseSettings):
    CHART_MCP_COMMAND: str = "npx"
    CHART_MCP_ARGS: str = "-y @ax-crew/chartjs-mcp-server"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ChartMCPService:
    def __init__(self, settings: ChartMCPSettings | None = None) -> None:
        self.settings = settings or ChartMCPSettings()
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._reconnect_lock = asyncio.Lock()

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise ChartMCPServiceError("Chart MCP session is not initialized")
        return self._session

    async def start(self) -> None:
        if self._session is not None:
            return

        stack = AsyncExitStack()
        server_params = StdioServerParameters(
            command=self.settings.CHART_MCP_COMMAND,
            args=self._parse_args(self.settings.CHART_MCP_ARGS),
        )
        read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()

        self._stack = stack
        self._session = session

    async def stop(self) -> None:
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except Exception:
                pass
        self._stack = None
        self._session = None

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._with_reconnect(lambda: self.session.call_tool(name, arguments=arguments))
        payload = result.model_dump(by_alias=True, exclude_none=True)
        if result.isError:
            raise ChartMCPServiceError(f"Chart MCP tool call failed: {payload}")
        return payload

    @staticmethod
    def _parse_args(raw_args: str) -> list[str]:
        cleaned_args = raw_args.strip()
        if not cleaned_args:
            return []
        if cleaned_args.startswith("["):
            try:
                parsed = json.loads(cleaned_args)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                return parsed
        return shlex.split(cleaned_args, posix=False)

    async def render_chart_html(self, *, chart_config: dict[str, Any]) -> str:
        payload = await self.call_tool(
            "generateChart",
            {
                "chartConfig": chart_config,
                "outputFormat": "html",
            },
        )
        parsed = self.extract_tool_data(payload)
        html_snippet = parsed.get("htmlSnippet")
        if not isinstance(html_snippet, str) or not html_snippet.strip():
            raw_html = parsed.get("rawHtml")
            if isinstance(raw_html, str) and raw_html.strip():
                html_snippet = raw_html
        success = parsed.get("success")
        if success is False:
            raise ChartMCPServiceError(parsed.get("error") or parsed.get("message") or "Chart MCP render failed")
        if not isinstance(html_snippet, str) or not html_snippet.strip():
            raise ChartMCPServiceError(f"Chart MCP did not return htmlSnippet: {parsed}")
        return html_snippet

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
            "not initialized",
        )
        return any(keyword in message for keyword in keywords) or isinstance(
            exc, (ConnectionError, ConnectionResetError, BrokenPipeError)
        )

    @staticmethod
    def extract_tool_data(payload: dict[str, Any]) -> dict[str, Any]:
        if "structuredContent" in payload and isinstance(payload["structuredContent"], dict):
            return payload["structuredContent"]

        content = payload.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if "json" in item and isinstance(item["json"], dict):
                    return item["json"]
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text = item["text"]
                    try:
                        parsed = json.loads(text)
                    except json.JSONDecodeError:
                        if "<canvas" in text or "<script" in text or "<div" in text:
                            return {"success": True, "rawHtml": text}
                        continue
                    if isinstance(parsed, dict):
                        return parsed
        return payload
