from __future__ import annotations

"""HTTP client wrapper for calling the standalone agent-core service."""

import json
from typing import Any

import httpx


class AgentCoreClientError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class AgentCoreClient:
    """Thin async client for forwarding chat requests to agent-core."""

    def __init__(self, *, base_url: str, handle_path: str, timeout_sec: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.handle_path = handle_path if handle_path.startswith("/") else f"/{handle_path}"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout_sec)

    async def close(self) -> None:
        await self.client.aclose()

    async def handle(
        self,
        *,
        question: str,
        max_rows: int | None,
        session_id: str | None,
    ) -> dict[str, Any]:
        payload = {
            "question": question,
            "max_rows": max_rows,
            "session_id": session_id,
        }
        try:
            response = await self.client.post(self.handle_path, json=payload)
        except httpx.TimeoutException as exc:
            raise AgentCoreClientError(status_code=504, detail="Timed out while calling agent-core") from exc
        except httpx.HTTPError as exc:
            raise AgentCoreClientError(status_code=502, detail=f"Failed to reach agent-core: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_error_detail(response)
            if 400 <= response.status_code < 500:
                raise AgentCoreClientError(status_code=response.status_code, detail=detail)
            raise AgentCoreClientError(status_code=502, detail=f"Upstream agent-core error: {detail}")

        try:
            parsed = response.json()
        except json.JSONDecodeError as exc:
            raise AgentCoreClientError(status_code=502, detail="agent-core returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise AgentCoreClientError(status_code=502, detail="agent-core response must be a JSON object")
        return parsed


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except json.JSONDecodeError:
        text = response.text.strip()
        return text or f"HTTP {response.status_code}"

    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail
        return json.dumps(body, ensure_ascii=False)
    return str(body)
