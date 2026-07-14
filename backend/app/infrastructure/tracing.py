"""
OpenTelemetry tracing setup with automatic FastAPI/httpx instrumentation.
Sends traces to OpenObserver via OTLP.

Usage:
    from app.infrastructure.tracing import setup_tracing, get_tracer

    setup_tracing(app)  # called at startup
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("do_work") as span:
        span.set_attribute("key", "value")
"""

from __future__ import annotations

from typing import Optional

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

logger = structlog.get_logger(__name__)

_tracer_provider: Optional[TracerProvider] = None


def setup_tracing(
    app,
    *,
    service_name: str = "rizzbot-api",
    otlp_endpoint: str = "",
    console_export: bool = False,
    auth_header: str = "",
    sample_rate: float = 1.0,
) -> None:
    """Initialise OTel tracing and instrument FastAPI + httpx.

    Args:
        app: FastAPI application instance.
        service_name: Resource service name.
        otlp_endpoint: OTLP HTTP endpoint (e.g. "http://openobserver:5001/api/default/v1/traces").
                        If empty, traces go to the console exporter only.
        console_export: Also emit traces to stdout (useful for local dev).
        auth_header: Full `Authorization` header value (e.g. "Bearer <key>" or "Basic <b64>").
        sample_rate: Fraction of requests to sample (0.0–1.0). Default 1.0 (all).
                     Set to 0.1 to trace 10% of requests, reducing cost at scale.
    """
    global _tracer_provider

    if _tracer_provider is not None:
        logger.warning("otel_tracing_already_initialised")
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "2.0.0",
            "deployment.environment": (
                app.state.settings.environment
                if hasattr(app.state, "settings")
                else "development"
            ),
        }
    )

    sampler = ParentBased(TraceIdRatioBased(sample_rate))
    provider = TracerProvider(resource=resource, sampler=sampler)

    # OTLP exporter for OpenObserver
    if otlp_endpoint:
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, headers=headers)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info("otel_otlp_exporter_configured", endpoint=otlp_endpoint)

    # Console exporter for local development
    if console_export or not otlp_endpoint:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    # Auto-instrument FastAPI (captures route, method, status, duration)
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument httpx so every LLM HTTP call gets a child span
    HTTPXClientInstrumentor().instrument()

    logger.info("otel_tracing_initialised", service_name=service_name)


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a named OTel tracer.

    Usage:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my_span") as span:
            span.set_attribute("key", "value")
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Flush and shut down the tracer provider (called on app shutdown)."""
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
