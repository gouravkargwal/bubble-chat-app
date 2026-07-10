"""
Prometheus metrics for the RizzBot API + OTLP export to OpenObserver.

Provides RED metrics (Rate, Errors, Duration) for every request path,
plus application-level metrics for LLM calls, database operations, and
business events.

All metric wrappers update BOTH prometheus_client (for /metrics endpoint)
AND OpenTelemetry (for OTLP export to OpenObserver) simultaneously, so
every metric increment lands in OpenObserver dashboards.

Usage:
    from app.infrastructure.metrics import (
        llm_calls_total, http_requests_total, db_connections_in_use, ...
    )
    llm_calls_total.labels(model="gemini-2.0-flash", operation="vision", status="success").inc()
    db_connections_in_use.set(5)
"""

from __future__ import annotations

from typing import Optional

import structlog
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import Counter as PromCounter, Gauge as PromGauge, Histogram as PromHistogram
from prometheus_fastapi_instrumentator import Instrumentator

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# OTel bridge wrappers
# ---------------------------------------------------------------------------
# Every prometheus_client Counter / Gauge / Histogram below is wrapped so that
# .inc() / .set() / .observe() also updates an OpenTelemetry instrument.
# The OTel instruments are created lazily when setup_otel_metrics() is called.
# Until then, calls pass through to prometheus_client only.

_otel_meter: object = None  # set by setup_otel_metrics()


def _get_otel_counter(name: str, unit: str = "1", description: str = "") -> object:
    """Return an OTel Counter from the global meter, or a no-op stub."""
    if _otel_meter is None:
        return _NoopOtelCounter()
    try:
        return _otel_meter.create_counter(name=name, unit=unit, description=description)
    except Exception:
        return _NoopOtelCounter()


def _get_otel_histogram(name: str, unit: str = "s", description: str = "") -> object:
    """Return an OTel Histogram from the global meter, or a no-op stub."""
    if _otel_meter is None:
        return _NoopOtelHistogram()
    try:
        return _otel_meter.create_histogram(name=name, unit=unit, description=description)
    except Exception:
        return _NoopOtelHistogram()


def _get_otel_gauge(name: str, unit: str = "1", description: str = "") -> object:
    """Return an OTel Gauge from the global meter, or a no-op stub."""
    if _otel_meter is None:
        return _NoopOtelGauge()
    try:
        # OTel Gauge was stabilised in the metrics API. Use create_gauge if available,
        # otherwise fall back to UpDownCounter semantics.
        return _otel_meter.create_gauge(name=name, unit=unit, description=description)
    except AttributeError:
        # Older OTel SDK — use UpDownCounter as a proxy
        return _otel_meter.create_up_down_counter(
            name=name, unit=unit, description=description
        )
    except Exception:
        return _NoopOtelGauge()


# ---------------------------------------------------------------------------
# No-op stubs — used before setup_otel_metrics() is called
# ---------------------------------------------------------------------------


class _NoopOtelCounter:
    def add(self, amount: int | float, attributes: dict | None = None) -> None:
        pass


class _NoopOtelHistogram:
    def record(self, amount: int | float, attributes: dict | None = None) -> None:
        pass


class _NoopOtelGauge:
    def set(self, value: int | float, attributes: dict | None = None) -> None:
        pass
    def add(self, amount: int | float, attributes: dict | None = None) -> None:
        pass


# ---------------------------------------------------------------------------
# Wrapper classes
# ---------------------------------------------------------------------------


class _DualCounterLabels:
    """Holds both prometheus label child and OTel attribute dict for a Counter."""

    __slots__ = ("_prom", "_otel", "_attrs", "_otel_counter")

    def __init__(self, prom_child, otel_counter, attrs: dict):
        self._prom = prom_child
        self._otel_counter = otel_counter
        self._attrs = attrs

    def inc(self, amount: int | float = 1) -> None:
        self._prom.inc(amount)
        self._otel_counter.add(amount, self._attrs)


class DualCounter:
    """Wraps a Prometheus Counter and an OTel Counter, updating both on .inc()."""

    def __init__(self, name: str, documentation: str, labelnames: tuple[str, ...] | list[str]):
        self._prom = PromCounter(name, documentation, labelnames=list(labelnames))
        self._name = name
        self._doc = documentation
        self._labelnames = list(labelnames)
        self._otel = None  # lazy

    def _ensure_otel(self) -> object:
        if self._otel is None:
            self._otel = _get_otel_counter(self._name, description=self._doc)
        return self._otel

    def labels(self, **labels) -> _DualCounterLabels:
        prom_child = self._prom.labels(**labels)
        otel_count = self._ensure_otel()
        # Filter labelnames to only those that match the OTel counter's known attributes.
        # We pass all labels and let the SDK handle unknown attributes gracefully.
        return _DualCounterLabels(prom_child, otel_count, labels)

    def inc(self, amount: int | float = 1) -> None:
        """Increment without any labels (total counter)."""
        self._prom.inc(amount)
        self._ensure_otel().add(amount, {})


class _DualHistogramLabels:
    __slots__ = ("_prom", "_otel", "_attrs", "_otel_histogram")

    def __init__(self, prom_child, otel_histogram, attrs: dict):
        self._prom = prom_child
        self._otel_histogram = otel_histogram
        self._attrs = attrs

    def observe(self, amount: int | float) -> None:
        self._prom.observe(amount)
        self._otel_histogram.record(amount, self._attrs)


class DualHistogram:
    """Wraps a Prometheus Histogram and OTel Histogram."""

    def __init__(self, name: str, documentation: str, labelnames: tuple[str, ...] | list[str], buckets: tuple | None = None):
        kwargs = {"name": name, "documentation": documentation, "labelnames": list(labelnames)}
        if buckets is not None:
            kwargs["buckets"] = buckets
        self._prom = PromHistogram(**kwargs)
        self._name = name
        self._doc = documentation
        self._labelnames = list(labelnames)
        self._otel = None

    def _ensure_otel(self) -> object:
        if self._otel is None:
            self._otel = _get_otel_histogram(self._name, description=self._doc)
        return self._otel

    def labels(self, **labels) -> _DualHistogramLabels:
        prom_child = self._prom.labels(**labels)
        otel_hist = self._ensure_otel()
        return _DualHistogramLabels(prom_child, otel_hist, labels)

    def observe(self, amount: int | float) -> None:
        self._prom.observe(amount)
        self._ensure_otel().record(amount, {})


class _DualGaugeLabels:
    __slots__ = ("_prom", "_otel", "_attrs", "_otel_gauge")

    def __init__(self, prom_child, otel_gauge, attrs: dict):
        self._prom = prom_child
        self._otel_gauge = otel_gauge
        self._attrs = attrs

    def set(self, value: int | float) -> None:
        self._prom.set(value)
        # OTel Gauge uses .set(); UpDownCounter uses .add(amount).
        # If the SDK only exposes UpDownCounter, we can't compute the delta
        # from an absolute set() call, so we log a warning and skip.
        if hasattr(self._otel_gauge, "set"):
            self._otel_gauge.set(value, self._attrs)
        else:
            logger.warning(
                "otel_gauge_set_skipped",
                _metric=self._prom._name,
                _reason="OTel SDK does not support Gauge.set(), only UpDownCounter.add()",
            )

    def inc(self, amount: int | float = 1) -> None:
        self._prom.inc(amount)
        if hasattr(self._otel_gauge, "add"):
            self._otel_gauge.add(amount, self._attrs)

    def dec(self, amount: int | float = 1) -> None:
        self._prom.dec(amount)
        if hasattr(self._otel_gauge, "add"):
            self._otel_gauge.add(-amount, self._attrs)


class DualGauge:
    """Wraps a Prometheus Gauge and OTel Gauge/UpDownCounter."""

    def __init__(self, name: str, documentation: str, labelnames: tuple[str, ...] | list[str] | None = None):
        self._prom = PromGauge(name, documentation, labelnames=list(labelnames or []))
        self._name = name
        self._doc = documentation
        self._labelnames = list(labelnames or [])
        self._otel = None

    def _ensure_otel(self) -> object:
        if self._otel is None:
            self._otel = _get_otel_gauge(self._name, description=self._doc)
        return self._otel

    def labels(self, **labels) -> _DualGaugeLabels:
        prom_child = self._prom.labels(**labels)
        otel_ga = self._ensure_otel()
        return _DualGaugeLabels(prom_child, otel_ga, labels)

    def set(self, value: int | float) -> None:
        self._prom.set(value)
        g = self._ensure_otel()
        if hasattr(g, "set"):
            g.set(value, {})

    def inc(self, amount: int | float = 1) -> None:
        self._prom.inc(amount)
        g = self._ensure_otel()
        if hasattr(g, "add"):
            g.add(amount, {})

    def dec(self, amount: int | float = 1) -> None:
        self._prom.dec(amount)
        g = self._ensure_otel()
        if hasattr(g, "add"):
            g.add(-amount, {})


# =========================================================================
#  Metric definitions — all use Dual* wrappers
# =========================================================================

# ---------------------------------------------------------------------------
# HTTP / API metrics (RED)
# ---------------------------------------------------------------------------

http_requests_total = DualCounter(
    "rizzbot_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status"],
)

http_request_duration_seconds = DualHistogram(
    "rizzbot_http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "path", "status"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# ---------------------------------------------------------------------------
# LLM / Gemini metrics
# ---------------------------------------------------------------------------

llm_calls_total = DualCounter(
    "rizzbot_llm_calls_total",
    "Total LLM API calls",
    labelnames=["model", "operation", "status"],
)

llm_latency_seconds = DualHistogram(
    "rizzbot_llm_latency_seconds",
    "LLM call latency in seconds",
    labelnames=["model", "operation"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

llm_tokens_total = DualCounter(
    "rizzbot_llm_tokens_total",
    "Total tokens consumed by LLM calls",
    labelnames=["model", "operation", "token_type"],  # token_type = "input" | "output"
)

llm_fallback_total = DualCounter(
    "rizzbot_llm_fallback_total",
    "Number of times fallback model was activated",
    labelnames=["primary_model", "fallback_model", "reason"],
)

# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

llm_cost_total = DualCounter(
    "rizzbot_llm_cost_total",
    "Accumulated LLM cost in USD",
    labelnames=["model", "operation"],
)

# ---------------------------------------------------------------------------
# Business / domain metrics
# ---------------------------------------------------------------------------

audit_jobs_total = DualCounter(
    "rizzbot_audit_jobs_total",
    "Profile audit jobs processed",
    labelnames=["status"],  # success, failed, cached, skipped
)

blueprint_generations_total = DualCounter(
    "rizzbot_blueprint_generations_total",
    "Profile blueprint generations",
    labelnames=["status"],  # success, failed, cached
)

# ---------------------------------------------------------------------------
# Resource / saturation metrics
# ---------------------------------------------------------------------------

db_connections_in_use = DualGauge(
    "rizzbot_db_connections_in_use",
    "Number of database connections currently checked out from the pool",
)

active_audit_workers = DualGauge(
    "rizzbot_active_audit_workers",
    "Number of audit workers currently processing jobs",
)

# ---------------------------------------------------------------------------
# Error taxonomy
# ---------------------------------------------------------------------------

error_total = DualCounter(
    "rizzbot_error_total",
    "Application errors classified by layer and severity",
    labelnames=["layer", "severity", "error_type"],
)

notification_failures_total = DualCounter(
    "rizzbot_notification_failures_total",
    "Push notification delivery failures by channel",
    labelnames=["channel", "reason"],
)

# ---------------------------------------------------------------------------
# Cache / tier service metrics
# ---------------------------------------------------------------------------

cache_hits_total = DualCounter(
    "rizzbot_cache_hits_total",
    "Cache hits by cache layer",
    labelnames=["layer"],
)

cache_misses_total = DualCounter(
    "rizzbot_cache_misses_total",
    "Cache misses by cache layer",
    labelnames=["layer"],
)

tier_allocations_total = DualCounter(
    "rizzbot_tier_allocations_total",
    "Model tier allocations by user tier",
    labelnames=["user_tier", "allocated_model"],
)


# =========================================================================
#  Instrumentator setup (auto-registers on FastAPI app)
# =========================================================================

_instrumentator: Optional[Instrumentator] = None


def setup_metrics(app, *, service_name: str = "api") -> None:
    """Attach Prometheus middleware + /metrics endpoint to a FastAPI application."""
    global _instrumentator

    _instrumentator = (
        Instrumentator()
        .instrument(app)
        .expose(
            app, endpoint="/metrics", include_in_schema=False, tags=["observability"]
        )
    )


def get_instrumentator() -> Optional[Instrumentator]:
    return _instrumentator


# =========================================================================
#  OpenTelemetry metrics export to OpenObserver
# =========================================================================

_otel_meter_provider: Optional[MeterProvider] = None


def setup_otel_metrics(
    *,
    endpoint: str = "",
    auth_header: str = "",
    service_name: str = "rizzbot-api",
) -> None:
    """Configure OTLP metric export to OpenObserver.

    Creates a global MeterProvider and meter. The Dual* metric wrappers
    already defined above will lazily create their OTel counterparts from
    this meter on first use, so existing code that calls .inc() / .set()
    / .observe() on them will automatically start exporting to OpenObserver.

    Args:
        endpoint: OTLP HTTP endpoint for metrics
            (e.g. "http://openobserver:5001/v1/otlp/metrics").
        auth_header: Full `Authorization` header value (e.g. "Bearer <key>" or "Basic <b64>").
        service_name: Service name for resource attributes.
    """
    global _otel_meter_provider, _otel_meter

    if _otel_meter_provider is not None:
        logger.warning("otel_metrics_already_initialised")
        return

    if not endpoint:
        logger.info("otel_metrics_skipped_no_endpoint")
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "2.0.0",
        }
    )

    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    otlp_exporter = OTLPMetricExporter(endpoint=endpoint, headers=headers)
    reader = PeriodicExportingMetricReader(
        otlp_exporter, export_interval_millis=30_000  # flush every 30 s
    )

    provider = MeterProvider(resource=resource, metric_readers=[reader])
    from opentelemetry import metrics as otel_metrics_api

    otel_metrics_api.set_meter_provider(provider)
    _otel_meter_provider = provider
    _otel_meter = otel_metrics_api.get_meter(service_name, version="2.0.0")

    logger.info(
        "otel_metrics_export_configured",
        endpoint=endpoint,
        meter_version="2.0.0",
    )


def shutdown_otel_metrics() -> None:
    """Flush and shut down the OTel MeterProvider (called on app shutdown)."""
    global _otel_meter_provider, _otel_meter
    if _otel_meter_provider is not None:
        try:
            _otel_meter_provider.shutdown()
        except Exception as exc:
            logger.warning("otel_metrics_shutdown_error", error=str(exc))
        _otel_meter_provider = None
        _otel_meter = None
