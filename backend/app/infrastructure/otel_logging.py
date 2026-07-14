"""
OpenTelemetry log export for OpenObserver.

Exports structured logs via OTLP to OpenObserver for unified observability.
Provides automatic trace-log correlation via trace_id.

Usage:
    from app.infrastructure.otel_logging import setup_otel_logging

    setup_otel_logging(
        endpoint="http://openobserver:5001/api/default/v1/logs",
        auth_header="Bearer your-api-key",
        service_name="rizzbot-api",
    )
"""

from __future__ import annotations

import logging
from typing import Optional

import structlog
from opentelemetry import _logs as otel_logs
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs._internal import LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.resources import Resource

_SCALAR_TYPES = (str, int, float, bool)


class _StructlogLoggingHandler(LoggingHandler):
    """Promotes structlog's event dict to top-level OTel log attributes.

    Without this, ``record.msg`` is the raw structlog event dict (structlog's
    ProcessorFormatter defers JSON-rendering to the stdout handler's own
    formatter), and the base LoggingHandler exports non-string ``record.msg``
    objects as the log's nested ``body`` value verbatim. OpenObserve then
    flattens that nested object into ``body_<key>`` columns instead of clean
    top-level fields like ``event``/``error_type``/``layer``.
    """

    def _translate(self, record: logging.LogRecord) -> LogRecord:
        otel_record = super()._translate(record)
        event_dict = record.msg
        if isinstance(event_dict, dict):
            otel_record.body = str(event_dict.get("event", otel_record.body))
            extra_attrs = {
                k: v
                for k, v in event_dict.items()
                if k != "event" and isinstance(v, _SCALAR_TYPES)
            }
            otel_record.attributes = {**(otel_record.attributes or {}), **extra_attrs}
        return otel_record


def setup_otel_logging(
    *,
    endpoint: str = "",
    auth_header: str = "",
    service_name: str = "rizzbot-api",
    console_export: bool = False,
) -> Optional[LoggingHandler]:
    """Configure OpenTelemetry log export to OpenObserver.

    Args:
        endpoint: OTLP HTTP endpoint for logs (e.g. "http://openobserver:5001/v1/otlp/logs").
        auth_header: Full `Authorization` header value (e.g. "Bearer <key>" or "Basic <b64>").
        service_name: Service name for resource attributes.
        console_export: Also emit logs to stdout.

    Returns:
        LoggingHandler instance for stdlib logging integration.
    """
    if not endpoint:
        # Fall back to console export for local development
        console_export = True

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "2.0.0",
        }
    )

    provider = LoggerProvider(resource=resource)

    # OTLP exporter for OpenObserver
    if endpoint:
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        otlp_exporter = OTLPLogExporter(endpoint=endpoint, headers=headers)
        # Batch records so each log line isn't a separate synchronous HTTP export
        # to OpenObserve. Exports on a background thread when the queue fills or
        # the schedule delay elapses, drastically reducing network overhead.
        provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

    # Console exporter for local development
    if console_export:
        provider.add_log_record_processor(ConsoleLogExporter())

    otel_logs.set_logger_provider(provider)

    # Bridge stdlib logging to OpenTelemetry
    handler = _StructlogLoggingHandler(logger_provider=provider)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    return handler


def get_log_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get an OpenTelemetry-aware structlog logger."""
    return structlog.get_logger(name)
