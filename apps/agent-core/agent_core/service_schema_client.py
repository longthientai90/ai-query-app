from __future__ import annotations

import json
from typing import Any

import httpx

from .settings import AgentCoreSettings
from telemetry import get_tracer

tracer = get_tracer(__name__)


class ServiceSchemaClientError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ServiceSchemaClient:
    """Thin async client for retrieving compact schema context from service-schema."""

    def __init__(self, settings: AgentCoreSettings) -> None:
        self.base_url = settings.SERVICE_SCHEMA_BASE_URL.rstrip("/")
        self.search_path = _normalize_path(settings.SERVICE_SCHEMA_SEARCH_PATH)
        self.reindex_path = _normalize_path(settings.SERVICE_SCHEMA_REINDEX_PATH)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=settings.SERVICE_SCHEMA_TIMEOUT_SEC,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def search(
        self,
        *,
        query: str,
        max_tables: int,
        include_indexes: bool,
        include_relationships: bool,
    ) -> dict[str, Any]:
        payload = {
            "query": query,
            "max_tables": max_tables,
            "include_indexes": include_indexes,
            "include_relationships": include_relationships,
        }
        return await self._post_json(self.search_path, payload, span_name="agent.service_schema.search")

    async def reindex(self, *, include_indexes: bool) -> dict[str, Any]:
        payload = {"include_indexes": include_indexes}
        return await self._post_json(self.reindex_path, payload, span_name="agent.service_schema.reindex")

    async def _post_json(self, path: str, payload: dict[str, Any], *, span_name: str) -> dict[str, Any]:
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("upstream.base_url", self.base_url)
            span.set_attribute("upstream.path", path)
            try:
                response = await self.client.post(path, json=payload)
            except httpx.TimeoutException as exc:
                span.set_attribute("error", True)
                span.set_attribute("error.type", "TimeoutException")
                raise ServiceSchemaClientError(
                    status_code=504,
                    detail="Timed out while calling service-schema",
                ) from exc
            except httpx.HTTPError as exc:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(exc).__name__)
                raise ServiceSchemaClientError(
                    status_code=502,
                    detail=f"Failed to reach service-schema: {exc}",
                ) from exc

            span.set_attribute("http.status_code", response.status_code)
            if response.status_code >= 400:
                span.set_attribute("error", True)
                detail = _extract_error_detail(response)
                raise ServiceSchemaClientError(status_code=response.status_code, detail=detail)

            try:
                parsed = response.json()
            except json.JSONDecodeError as exc:
                span.set_attribute("error", True)
                span.set_attribute("error.type", "JSONDecodeError")
                raise ServiceSchemaClientError(
                    status_code=502,
                    detail="service-schema returned invalid JSON",
                ) from exc
            if not isinstance(parsed, dict):
                span.set_attribute("error", True)
                span.set_attribute("error.type", "InvalidResponseShape")
                raise ServiceSchemaClientError(
                    status_code=502,
                    detail="service-schema response must be a JSON object",
                )
            return parsed


def _normalize_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


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
