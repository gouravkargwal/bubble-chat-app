import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
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

# Infrastructure-level rate limiter (IP-based, complements application-level quotas)
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            environment=settings.environment,
            release="rizzbot-backend@2.0.0",
        )

    await init_db()
    yield




def create_app() -> FastAPI:
    setup_logging(settings.log_level, json_logs=settings.log_json)

    app = FastAPI(
        title="RizzBot API",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Infrastructure-level rate limiting (IP-based, defense-in-depth)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
        if "vision/generate" not in request.url.path:
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

    # Correlation ID: header passthrough (gateway / client) or new UUID; bound to structlog
    # for the whole request so JSON logs shipped to Loki share one correlation_id per lifecycle.
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        incoming = (
            request.headers.get("X-Correlation-ID")
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
