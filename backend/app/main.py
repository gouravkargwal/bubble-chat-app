import json
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pyinstrument import Profiler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.datastructures import Headers, MutableHeaders

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


def _security_headers(environment: str) -> dict[str, str]:
    headers = {
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        ),
    }
    if environment != "development":
        headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    return headers


def _cors_headers(origin: str, allowed: list[str]) -> dict[str, str]:
    if "*" in allowed:
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    if origin in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    return {}


class RequestPipelineMiddleware:
    """Correlation ID, profiling, payload limit, RED metrics, CORS, and
    security headers — as a single pure-ASGI middleware.

    NOTE: This used to be five (then one) `@app.middleware("http")`
    functions. Starlette implements those via BaseHTTPMiddleware, which
    drains the inner app's response into a buffer and re-streams it against
    the original Content-Length; under a client disconnect mid-response that
    re-stream can raise "RuntimeError: Response content shorter than
    Content-Length" even though the endpoint itself returned a perfectly
    normal response. Speaking raw ASGI means body chunks from the inner app
    pass straight through to the real `send` untouched — we only ever
    inject headers into `http.response.start` — so there is no buffered
    re-stream left to fail.
    """

    def __init__(self, app: Any, max_payload_bytes: int) -> None:
        self.app = app
        self.max_payload_bytes = max_payload_bytes

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        method = scope["method"]
        path = scope["path"]

        traceparent = headers.get("traceparent", "")
        trace_id_from_traceparent = ""
        parts = traceparent.split("-")
        if len(parts) == 4 and len(parts[1]) == 32:
            trace_id_from_traceparent = parts[1]

        incoming = (
            trace_id_from_traceparent
            or headers.get("x-correlation-id")
            or headers.get("x-request-id")
            or ""
        ).strip()
        cid = incoming or str(uuid.uuid4())
        scope.setdefault("state", {})["correlation_id"] = cid

        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        _ctx = _span.get_span_context() if _span else None
        structlog.contextvars.bind_contextvars(
            correlation_id=cid,
            trace_id=(format(_ctx.trace_id, "032x") if _ctx and _ctx.is_valid else ""),
            span_id=(format(_ctx.span_id, "016x") if _ctx and _ctx.is_valid else ""),
            http_method=method,
            http_path=path,
        )

        origin = headers.get("origin", "")
        allowed = settings.cors_origins
        response_status = 200
        start = time.monotonic()

        try:
            if method == "OPTIONS":
                await self._send_preflight(send, origin=origin, allowed=allowed, cid=cid)
                response_status = 200
                return

            content_length = headers.get("content-length")
            if (
                path.startswith("/api/public")
                and content_length
                and int(content_length) > self.max_payload_bytes
            ):
                response_status = 413
                await self._send_json(
                    send,
                    status=413,
                    content={
                        "detail": f"File too large. Max {settings.lead_magnet_max_payload_mb} MB."
                    },
                    origin=origin,
                    allowed=allowed,
                    cid=cid,
                    path=path,
                )
                return

            profiling = "vision/generate_v2" in path
            profiler = None
            if profiling:
                profiler = Profiler(interval=0.001, async_mode="enabled")
                profiler.start()

            async def send_wrapper(message: Any) -> None:
                nonlocal response_status
                if message["type"] == "http.response.start":
                    response_status = message["status"]
                    mutable_headers = MutableHeaders(raw=message["headers"])
                    self._apply_response_headers(
                        mutable_headers, origin=origin, allowed=allowed, cid=cid, path=path
                    )
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                if profiler is not None:
                    profiler.stop()
                    # Write HTML report to project root (WORKDIR is /app in Docker)
                    html_output = profiler.output_html()
                    with open("profile_results.html", "w", encoding="utf-8") as f:
                        f.write(html_output)
        finally:
            duration = time.monotonic() - start
            labels = {"method": method, "path": path, "status": str(response_status)}
            http_requests_total.labels(**labels).inc()
            http_request_duration_seconds.labels(**labels).observe(duration)
            structlog.contextvars.unbind_contextvars(
                "correlation_id",
                "trace_id",
                "span_id",
                "http_method",
                "http_path",
            )

    def _apply_response_headers(
        self,
        headers: MutableHeaders,
        *,
        origin: str,
        allowed: list[str],
        cid: str,
        path: str,
    ) -> None:
        for name, value in _cors_headers(origin, allowed).items():
            headers[name] = value
        for name, value in _security_headers(settings.environment).items():
            headers[name] = value
        if not path.startswith("/static/") and "cache-control" not in headers:
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        headers["X-Correlation-ID"] = cid

    async def _send_preflight(
        self, send: Any, *, origin: str, allowed: list[str], cid: str
    ) -> None:
        header_dict = {**_cors_headers(origin, allowed), "X-Correlation-ID": cid}
        raw_headers = [
            (k.encode("latin-1"), v.encode("latin-1")) for k, v in header_dict.items()
        ]
        await send(
            {"type": "http.response.start", "status": 200, "headers": raw_headers}
        )
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _send_json(
        self,
        send: Any,
        *,
        status: int,
        content: dict[str, Any],
        origin: str,
        allowed: list[str],
        cid: str,
        path: str,
    ) -> None:
        body = json.dumps(content).encode("utf-8")
        raw_headers = [(b"content-type", b"application/json")]
        mutable_headers = MutableHeaders(raw=raw_headers)
        mutable_headers["content-length"] = str(len(body))
        self._apply_response_headers(
            mutable_headers, origin=origin, allowed=allowed, cid=cid, path=path
        )
        await send(
            {"type": "http.response.start", "status": status, "headers": raw_headers}
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})


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
        title="Cookd API",
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
    # metrics, CORS, security headers) — pure ASGI, see RequestPipelineMiddleware
    # for why this isn't a BaseHTTPMiddleware.
    app.add_middleware(RequestPipelineMiddleware, max_payload_bytes=max_payload_bytes)

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
