from __future__ import annotations

"""OpenTelemetry bootstrap helpers for mcp-query-server."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(*, service_name: str) -> None:
    """Configure an OTLP exporter and tracer provider for this process."""
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


def get_tracer(name: str):
    return trace.get_tracer(name)
