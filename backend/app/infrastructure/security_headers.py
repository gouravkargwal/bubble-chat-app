"""
Security headers — add hardening headers to every HTTP response.

Used as an @app.middleware("http") in main.py.  Adds CSP, HSTS,
X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and
Permissions-Policy headers.  These are redundant with a reverse-proxy
layer but provide defence-in-depth for any path that bypasses the proxy.
"""

from __future__ import annotations

from fastapi import Request, Response

from app.config import settings


async def add_security_headers(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """ASGI middleware: add security headers to every response.

    Registered in main.py via @app.middleware("http") to stay consistent
    with the correlation-id and RED-metrics middlewares.
    """
    response: Response = await call_next(request)

    # ── Content-Security-Policy ──────────────────────────────────────────
    # Restricts script/style sources to reduce XSS blast radius.
    #
    # 'unsafe-inline' + 'unsafe-eval' for scripts: required by Prometheus
    # /metrics page (inline JS charts) and pyinstrument profiling HTML.
    # If neither is needed, tighten to:
    #   script-src 'self'; style-src 'self' 'unsafe-inline'
    #
    # PayU domains are allowed in form-action so the hidden POST form
    # on the LTD checkout page can submit to PayU.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self' https://test.payu.in https://secure.payu.in"
    )

    # ── X-Content-Type-Options ───────────────────────────────────────────
    # Prevents MIME-type sniffing (e.g. interpreting a .txt as .html).
    response.headers["X-Content-Type-Options"] = "nosniff"

    # ── X-Frame-Options ──────────────────────────────────────────────────
    # Prevents clickjacking by blocking rendering in <frame>/<iframe>.
    response.headers["X-Frame-Options"] = "DENY"

    # ── Referrer-Policy ──────────────────────────────────────────────────
    # Controls what referrer info is sent with cross-origin requests.
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # ── Permissions-Policy ───────────────────────────────────────────────
    # Restricts which browser APIs the page can use (camera, mic, etc.).
    response.headers["Permissions-Policy"] = (
        "camera=(), " "microphone=(), " "geolocation=(), " "interest-cohort=()"
    )

    # ── Strict-Transport-Security (HSTS) ────────────────────────────────
    # Only set in non-development environments when served over HTTPS.
    # Forces browsers to always use HTTPS for this domain.
    if settings.environment != "development":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    # ── Cache-Control for API responses ──────────────────────────────────
    # Prevent caching of API responses (mobile clients should not
    # cache sensitive data).  Does not apply to /static/ paths.
    if not request.url.path.startswith("/static/"):
        response.headers.setdefault(
            "Cache-Control", "no-store, no-cache, must-revalidate"
        )

    return response
