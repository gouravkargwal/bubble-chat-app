import logging
from typing import Any

import structlog


_NAME_TO_LEVEL = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _sentry_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Send ERROR-level (and above) log entries to Sentry as breadcrumbs / events."""
    level = event_dict.get("level", "")
    if level in ("error", "critical"):
        try:
            import sentry_sdk

            exc_info = event_dict.get("exc_info")
            if exc_info:
                sentry_sdk.capture_exception(exc_info)
            else:
                sentry_sdk.capture_message(
                    event_dict.get("event", str(event_dict)),
                    level=level,
                )
        except ImportError:
            pass
    return event_dict


def _add_request_id(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject request_id / correlation_id from structlog context-vars if present."""
    # structlog.contextvars.merge_contextvars already merges bound context;
    # this processor ensures the key is always surfaced even when not explicitly bound.
    if "request_id" not in event_dict and "correlation_id" not in event_dict:
        event_dict.setdefault("request_id", None)
    return event_dict


def setup_logging(level: str = "INFO") -> None:
    log_level = _NAME_TO_LEVEL.get(level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_request_id,
            _sentry_processor,
            structlog.dev.ConsoleRenderer()
            if level == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
