import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace

_NAME_TO_LEVEL = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class _QuietAccessLogFilter(logging.Filter):
    """Drop high-churn access lines from stdout/Loki (health checks, polled JSON APIs).

    Successful GETs to common mobile polling endpoints generate multiple identical
    lines per screen load; load balancers often already retain access logs.
    Non-200 responses are always kept.
    """

    _QUIET_GET_PREFIXES = (
        "GET /health ",
        "HEAD /health ",
        "GET /api/v1/usage ",
        "GET /api/v1/preferences ",
        "GET /api/v1/referral/me ",
        "GET /api/v1/profile-audit/blueprints",
        # (removed: GET /api/v1/billing/ltd/banner-config was part of LTD/Payu)
        # Bot/crawler noise: 404s for common scanner paths
        "GET /robots.txt ",
        "GET /favicon.ico ",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if "GET /health" in msg or "HEAD /health" in msg:
            return False
        # Uvicorn: 'host - "GET /path HTTP/1.1" 200'
        if not msg.rstrip().endswith(" 200"):
            return True
        for prefix in self._QUIET_GET_PREFIXES:
            if prefix in msg:
                return False
        return True


def setup_logging(level: str = "INFO", *, json_logs: bool = True) -> None:
    """Configure structlog + stdlib logging so every logger emits one JSON line per event.

    ``json_logs=False`` uses ConsoleRenderer (human-readable) for local debugging.
    Uvicorn and ``logging.getLogger`` output go through the same formatter as structlog.
    """
    log_level = _NAME_TO_LEVEL.get(level.upper(), logging.INFO)

    from app.config import settings as app_settings

    def _add_service_fields(
        logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        event_dict.setdefault("service_name", app_settings.log_service_name)
        event_dict.setdefault("environment", app_settings.environment)
        return event_dict

    def _add_otel_trace_context(
        logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Inject the current OpenTelemetry trace_id and span_id into every log event.

        This enables log-to-trace correlation in OpenObserver: you can click from
        a log line to its corresponding trace waterfall.
        """
        span = trace.get_current_span()
        if span is not None:
            ctx = span.get_span_context()
            if ctx.is_valid:
                event_dict["trace_id"] = format(ctx.trace_id, "032x")
                event_dict["span_id"] = format(ctx.span_id, "016x")
        return event_dict

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    foreign_pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        _add_service_fields,
        _add_otel_trace_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *foreign_pre_chain,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=foreign_pre_chain,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # SQLAlchemy echo= would add a plain-text StreamHandler; clear and use root → JSON only.
    # Keep engine/pool at WARNING so emitted SQL is never logged at INFO (avoids Loki noise + data leakage).
    for name in ("sqlalchemy.engine", "sqlalchemy.pool"):
        sq = logging.getLogger(name)
        sq.handlers.clear()
        sq.propagate = True
        sq.setLevel(logging.WARNING)

    # Uvicorn attaches its own handlers; send those records through the root formatter.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
        lg.setLevel(log_level)
    logging.getLogger("uvicorn.access").addFilter(_QuietAccessLogFilter())
    # Set uvicorn.access to WARNING so its high-volume INFO lines (every request)
    # are never exported to OpenObserver via the OTel logging handler.
    # Successful 200 responses that aren't health endpoints are still logged at
    # their original severity by uvicorn itself, but only WARNING+ propagates to
    # the root OTel handler.  This eliminates ~99% of access log traffic in
    # OpenObserver without losing error/critical access lines.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    for name in ("httpx", "httpcore"):
        noisy = logging.getLogger(name)
        noisy.handlers.clear()
        noisy.propagate = True
        noisy.setLevel(logging.WARNING)
