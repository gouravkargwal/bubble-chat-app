"""Admin-only dependencies — protect internal endpoints from public access.

Usage:
    @router.get("/admin/...", dependencies=[Depends(verify_admin_key)])
"""

from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_admin_key(x_admin_key: str = Header(...)) -> None:
    """Guard admin endpoints with a shared secret.

    Only the Next.js BFF layer knows this key.  Public callers (Android app,
    random internet traffic) cannot reach these endpoints.
    """
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured on server.",
        )
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin API key.",
        )
