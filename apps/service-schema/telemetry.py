from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_httpx_instrumented = False


def setup_telemetry(*, app: FastAPI, service_name: str) -> None:
    _ensure_tracer_provider(service_name=service_name)
    _instrument_httpx_once()
    FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str):
    return trace.get_tracer(name)


def _ensure_tracer_provider(*, service_name: str) -> None:
    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        if getattr(current_provider, "_has_codex_otlp_processor", False):
            return
        current_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        setattr(current_provider, "_has_codex_otlp_processor", True)
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    setattr(provider, "_has_codex_otlp_processor", True)
    trace.set_tracer_provider(provider)


def _instrument_httpx_once() -> None:
    global _httpx_instrumented
    if _httpx_instrumented:
        return
    HTTPXClientInstrumentor().instrument()
    _httpx_instrumented = True
