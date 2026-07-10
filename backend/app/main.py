import json
import time
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import structlog
from pyinstrument import Profiler

from app.config import settings
from app.infrastructure.database.engine import init_db
from app.infrastructure.logging import setup_logging
from app.infrastructure.metrics import (
    setup_metrics,
    error_total,
    http_requests_total,
    http_request_duration_seconds,
)
from app.infrastructure.tracing import setup_tracing, shutdown_tracing
from app.infrastructure.otel_logging import setup_otel_logging

# Infrastructure-level rate limiter (IP-based, complements application-level quotas)
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


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
    # Sentry initialization (kept for error alerting)
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            environment=settings.environment,
            release="rizzbot-backend@2.0.0",
        )

    # OpenTelemetry — initialise exporters for OpenObserver
    if settings.otlp_enabled:
        # OpenObserve OTLP/HTTP ingestion is org-scoped: /api/{org}/v1/{signal}
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

    app = FastAPI(
        title="RizzBot API",
        version="2.0.0",
        lifespan=lifespan,
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

    # CORS — never combine wildcard origins with credentials
    is_wildcard = settings.cors_origins == ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=not is_wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Profiling middleware (limited to the vision generate endpoint)
    @app.middleware("http")
    async def profile_request(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        # Only profile the vision generate endpoint
        if "vision/generate_v2" not in request.url.path:
            return await call_next(request)

        profiler = Profiler(interval=0.001, async_mode="enabled")
        profiler.start()
        try:
            response: Response = await call_next(request)
        finally:
            profiler.stop()
            # Write HTML report to project root (WORKDIR is /app in Docker)
            html_output = profiler.output_html()
            with open("profile_results.html", "w", encoding="utf-8") as f:
                f.write(html_output)

        return response

    # RED metrics: request rate/errors/duration per (method, path, status)
    @app.middleware("http")
    async def record_red_metrics(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        start = time.monotonic()
        response: Response = await call_next(request)
        duration = time.monotonic() - start
        labels = {
            "method": request.method,
            "path": request.url.path,
            "status": str(response.status_code),
        }
        http_requests_total.labels(**labels).inc()
        http_request_duration_seconds.labels(**labels).observe(duration)
        return response

    # Correlation ID: prefer the W3C traceparent's trace-id (so logs and OTel
    # traces share one ID and can be pivoted between in OpenObserve), then
    # X-Correlation-ID/X-Request-ID passthrough, then a new UUID.
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
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
        structlog.contextvars.bind_contextvars(
            correlation_id=cid,
            http_method=request.method,
            http_path=request.url.path,
        )
        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            structlog.contextvars.unbind_contextvars(
                "correlation_id", "http_method", "http_path"
            )

    # Global exception handler — must NOT intercept HTTPException
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Let FastAPI handle its own HTTP exceptions (401, 403, 429, etc.)
        if isinstance(exc, HTTPException):
            raise exc

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

        # Forward to Sentry if initialised
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(exc)
        except ImportError:
            pass

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Routes
    from app.api.v1.router import v1_router

    app.include_router(v1_router, prefix="/api/v1")

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
