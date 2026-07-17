import json
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pyinstrument import Profiler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.infrastructure.database.engine import init_db
from app.infrastructure.logging import setup_logging
from app.infrastructure.metrics import (
    error_total,
    http_request_duration_seconds,
    http_requests_total,
    setup_metrics,
)
from app.infrastructure.otel_logging import setup_otel_logging
from app.infrastructure.ratelimit import limiter
from app.infrastructure.security_headers import add_security_headers
from app.infrastructure.tracing import setup_tracing, shutdown_tracing


def _detail_for_log(detail: Any, *, max_len: int = 4000) -> Any:
    """Normalize exception detail for structured logs (truncate huge bodies)."""
    if isinstance(detail, str):
        return detail if len(detail) <= max_len else detail[: max_len - 3] + "..."
    try:
        raw = json.dumps(detail, default=str)
    except (TypeError, ValueError):
        raw = str(detail)
    return raw if len(raw) <= max_len else raw[: max_len - 3] + "..."


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # OpenTelemetry — initialise exporters for OpenObserver (replaces Sentry)
    if settings.otlp_enabled:
        # OpenObserve OTLP/HTTP ingestion is org-scoped: /api/{org}/v1/{signal}
        # (the binary is env-var driven; it does not support custom paths).
        base_url = f"{settings.openobserver_endpoint.rstrip('/')}/api/{settings.zo_org}"
        traces_endpoint = f"{base_url}/v1/traces"
        logs_endpoint = f"{base_url}/v1/logs"

        try:
            auth_header = settings.openobserver_auth_header
            setup_tracing(
                app,
                service_name=settings.openobserver_service_name,
                otlp_endpoint=traces_endpoint,
                console_export=not settings.log_json,
                auth_header=auth_header,
                sample_rate=settings.otlp_sample_rate,
            )
            setup_otel_logging(
                endpoint=logs_endpoint,
                auth_header=auth_header,
                service_name=settings.openobserver_service_name,
                console_export=not settings.log_json,
            )
            from app.infrastructure.metrics import setup_otel_metrics

            setup_otel_metrics(
                endpoint=f"{base_url}/v1/metrics",
                auth_header=auth_header,
                service_name=settings.openobserver_service_name,
            )
        except Exception:
            logger = structlog.get_logger()
            logger.exception("openobserver_init_failed_nonfatal")

    await init_db()

    yield

    # Shutdown: flush remaining spans, flush metrics
    from app.infrastructure.metrics import shutdown_otel_metrics

    shutdown_tracing()
    shutdown_otel_metrics()


def create_app() -> FastAPI:
    setup_logging(settings.log_level, json_logs=settings.log_json)
    max_payload_bytes = settings.lead_magnet_max_payload_mb * 1024 * 1024

    app = FastAPI(
        title="RizzBot API",
        version="2.0.0",
        lifespan=lifespan,
        docs_url=None if settings.environment != "development" else "/docs",
        redoc_url=None if settings.environment != "development" else "/redoc",
    )

    # Prometheus metrics — exposes /metrics endpoint and instruments HTTP RED metrics
    setup_metrics(app)

    # Infrastructure-level rate limiting (IP-based, defense-in-depth)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(HTTPException)
    async def log_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        """Log client/server HTTP errors with enough context to debug access-log-only 4xx/5xx."""
        log = structlog.get_logger()
        cid = getattr(request.state, "correlation_id", None)
        status = exc.status_code
        detail_log = _detail_for_log(exc.detail)
        kw = {
            "status_code": status,
            "detail": detail_log,
            "http_method": request.method,
            "http_path": request.url.path,
            "correlation_id": cid,
        }
        if status >= 500:
            log.error("http_exception", **kw)
        elif status >= 400:
            log.warning("http_exception", **kw)
        else:
            log.info("http_exception", **kw)
        if status >= 400:
            error_total.labels(
                layer="api",
                severity="critical" if status >= 500 else "warning",
                error_type=type(exc).__name__,
            ).inc()
        return JSONResponse(status_code=status, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def log_validation_exception(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        log = structlog.get_logger()
        cid = getattr(request.state, "correlation_id", None)
        errors = exc.errors()
        sample = errors[:8]
        log.warning(
            "request_validation_error",
            status_code=422,
            error_count=len(errors),
            errors=_detail_for_log(sample, max_len=8000),
            http_method=request.method,
            http_path=request.url.path,
            correlation_id=cid,
        )
        return JSONResponse(status_code=422, content={"detail": errors})

    # ── Request pipeline (correlation ID, profiling, payload limit, RED
    # metrics, CORS, security headers) ──
    #
    # NOTE: This used to be five separate @app.middleware("http") functions.
    # Starlette implements each as a BaseHTTPMiddleware, and stacking several
    # of them wraps the response body in nested re-streaming layers; under a
    # client disconnect mid-response, that chain can raise
    # "RuntimeError: Response content shorter than Content-Length" even
    # though the endpoint itself returned a perfectly normal response.
    # Collapsing everything into one middleware removes the extra layers
    # (and, incidentally, still avoids the known CORSMiddleware +
    # BaseHTTPMiddleware incompatibility that ruled out fastapi's CORSMiddleware).
    @app.middleware("http")
    async def request_pipeline(request: Request, call_next) -> Response:
        # ── Correlation ID: prefer the W3C traceparent's trace-id (so logs
        # and OTel traces share one ID and can be pivoted between in
        # OpenObserve), then X-Correlation-ID/X-Request-ID, then a new UUID.
        traceparent = request.headers.get("traceparent", "")
        trace_id_from_traceparent = ""
        parts = traceparent.split("-")
        if len(parts) == 4 and len(parts[1]) == 32:
            trace_id_from_traceparent = parts[1]

        incoming = (
            trace_id_from_traceparent
            or request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or ""
        ).strip()
        cid = incoming or str(uuid.uuid4())
        request.state.correlation_id = cid

        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        _ctx = _span.get_span_context() if _span else None
        structlog.contextvars.bind_contextvars(
            correlation_id=cid,
            trace_id=(format(_ctx.trace_id, "032x") if _ctx and _ctx.is_valid else ""),
            span_id=(format(_ctx.span_id, "016x") if _ctx and _ctx.is_valid else ""),
            http_method=request.method,
            http_path=request.url.path,
        )

        try:
            start = time.monotonic()

            # Profiling middleware (limited to the vision generate endpoint)
            profiling = "vision/generate_v2" in request.url.path
            profiler = None
            if profiling:
                profiler = Profiler(interval=0.001, async_mode="enabled")
                profiler.start()

            try:
                # Payload size limit for public endpoints (prevent OOM on
                # large uploads)
                content_length = request.headers.get("content-length")
                if (
                    request.url.path.startswith("/api/public")
                    and content_length
                    and int(content_length) > max_payload_bytes
                ):
                    response: Response = JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"File too large. Max {settings.lead_magnet_max_payload_mb} MB."
                        },
                    )
                else:
                    response = await call_next(request)
            finally:
                if profiler is not None:
                    profiler.stop()
                    # Write HTML report to project root (WORKDIR is /app in Docker)
                    html_output = profiler.output_html()
                    with open("profile_results.html", "w", encoding="utf-8") as f:
                        f.write(html_output)

            # RED metrics: request rate/errors/duration per (method, path, status)
            duration = time.monotonic() - start
            labels = {
                "method": request.method,
                "path": request.url.path,
                "status": str(response.status_code),
            }
            http_requests_total.labels(**labels).inc()
            http_request_duration_seconds.labels(**labels).observe(duration)

            # ── CORS (add ACAO to every response) ──
            origin = request.headers.get("origin", "")
            allowed = settings.cors_origins
            if "*" in allowed:
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
            elif origin in allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization"
                )

            if request.method == "OPTIONS":
                # Handle OPTIONS preflight immediately
                response = Response(status_code=200, headers=dict(response.headers))
            else:
                # ── Security headers ──
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' data:; "
                    "object-src 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self' https://payu.in https://www.payu.in https://test.payu.in https://secure.payu.in https://api.payu.in https://apitest.payu.in"
                )
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Permissions-Policy"] = (
                    "camera=(), microphone=(), geolocation=(), interest-cohort=()"
                )
                if settings.environment != "development":
                    response.headers["Strict-Transport-Security"] = (
                        "max-age=31536000; includeSubDomains; preload"
                    )
                if not request.url.path.startswith("/static/"):
                    response.headers.setdefault(
                        "Cache-Control", "no-store, no-cache, must-revalidate"
                    )

            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            structlog.contextvars.unbind_contextvars(
                "correlation_id",
                "trace_id",
                "span_id",
                "http_method",
                "http_path",
            )

    # Global exception handler — must NOT intercept HTTPException
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Let FastAPI handle its own HTTP exceptions (401, 403, 429, etc.)
        if isinstance(exc, HTTPException):
            raise exc

        # Record the exception on the current OTel span so it appears as
        # a span event in the Traces tab (with type, message, stacktrace).
        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        if _span and _span.is_recording():
            _span.record_exception(exc)

        logger = structlog.get_logger()
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.error(
            "unhandled_exception",
            error=str(exc),
            exc_info=exc,
            path=request.url.path,
            correlation_id=correlation_id,
        )
        error_total.labels(
            layer="api", severity="critical", error_type=type(exc).__name__
        ).inc()

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Routes
    from app.api.v1.router import v1_router

    app.include_router(v1_router, prefix="/api/v1")

    # Public (no-auth) lead-magnet router
    from app.api.v1.public import router as public_router

    app.include_router(public_router, prefix="/api/v1/public")

    # Static files (for profile audit images, etc.)
    static_dir = Path("static")
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check with database connectivity verification."""
        from sqlalchemy import text

        from app.infrastructure.database.engine import get_db

        try:
            async for db in get_db():
                await db.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "version": "2.0.0",
                    "db": "unreachable",
                },
            )
        return {"status": "healthy", "version": "2.0.0", "db": "connected"}

    return app


app = create_app()
