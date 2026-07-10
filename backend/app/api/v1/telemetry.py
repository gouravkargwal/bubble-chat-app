"""Client (mobile app) telemetry — errors reported from the app land in the
same OpenObserve pipeline as backend errors, tagged layer="mobile"."""

import structlog
from fastapi import APIRouter, Depends, Request

from app.api.v1.deps import get_current_user
from app.api.v1.schemas.schemas import ClientErrorRequest
from app.infrastructure.database.models import User
from app.infrastructure.metrics import error_total

router = APIRouter()
logger = structlog.get_logger()


@router.post("/telemetry/client-error")
async def report_client_error(
    request: Request,
    body: ClientErrorRequest,
    user: User = Depends(get_current_user),
) -> dict:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.warning(
        "client_error",
        layer="mobile",
        error_type=body.error_type,
        message=body.message,
        screen=body.screen,
        severity=body.severity,
        app_version=body.app_version,
        os_version=body.os_version,
        device_model=body.device_model,
        stack_trace=body.stack_trace,
        user_id=user.id,
        correlation_id=correlation_id,
    )
    error_total.labels(
        layer="mobile", severity=body.severity, error_type=body.error_type
    ).inc()
    return {"status": "ok"}
