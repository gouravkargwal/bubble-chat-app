"""OCI Object Storage — Oracle Cloud only (no local filesystem fallback)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_oci_client = None
_oci_namespace: str | None = None
_oci_region: str | None = None


def _get_oci_client():
    """Lazily initialise the OCI ObjectStorageClient, namespace, and region."""
    global _oci_client, _oci_namespace, _oci_region

    if _oci_client is not None:
        return _oci_client, _oci_namespace

    import oci  # noqa: E402 — deferred import

    config_path = os.path.expanduser(settings.oci_config_file)
    config = oci.config.from_file(config_path, settings.oci_config_profile)
    _oci_client = oci.object_storage.ObjectStorageClient(config)
    _oci_region = (config.get("region") or "").strip() or "us-ashburn-1"

    if settings.oci_namespace:
        _oci_namespace = settings.oci_namespace
    else:
        _oci_namespace = _oci_client.get_namespace().data

    logger.info(
        "oci_storage_initialised",
        namespace=_oci_namespace,
        bucket=settings.oci_bucket_name,
        region=_oci_region,
    )
    return _oci_client, _oci_namespace


async def upload(object_name: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Upload bytes to OCI Object Storage. Returns object_name (storage key)."""
    try:
        client, namespace = _get_oci_client()
        client.put_object(
            namespace,
            settings.oci_bucket_name,
            object_name,
            data,
            content_type=content_type,
        )
        return object_name
    except Exception as e:
        logger.error("oci_upload_failed", object_name=object_name, error=str(e))
        raise


async def get_signed_url(object_name: str) -> str:
    """Generate a time-limited pre-authenticated request URL."""
    import oci

    try:
        client, namespace = _get_oci_client()
        expiry = datetime.now(timezone.utc) + timedelta(hours=settings.oci_par_expiry_hours)

        par_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
            name=f"par-{object_name.replace('/', '-')}-{int(expiry.timestamp())}",
            object_name=object_name,
            access_type="ObjectRead",
            time_expires=expiry,
        )
        par_response = client.create_preauthenticated_request(
            namespace,
            settings.oci_bucket_name,
            par_details,
        )
        par = par_response.data
        region = _oci_region or "us-ashburn-1"
        base = f"https://objectstorage.{region}.oraclecloud.com"
        return f"{base}{par.access_uri}"
    except Exception as e:
        logger.error("oci_signed_url_failed", object_name=object_name, error=str(e))
        raise


async def delete(object_name: str) -> bool:
    """Delete an object from OCI. Returns True on success."""
    try:
        client, namespace = _get_oci_client()
        client.delete_object(namespace, settings.oci_bucket_name, object_name)
        return True
    except Exception as e:
        logger.warning("oci_delete_failed", object_name=object_name, error=str(e))
        return False


async def get_bytes(object_name: str) -> bytes | None:
    """Download object bytes from OCI. Returns None only if the object does not exist (404)."""
    try:
        client, namespace = _get_oci_client()
        response = client.get_object(namespace, settings.oci_bucket_name, object_name)
        return response.data.content
    except Exception as e:
        from oci.exceptions import ServiceError  # type: ignore[import-untyped]

        if isinstance(e, ServiceError) and e.status == 404:
            return None
        logger.error("oci_get_bytes_failed", object_name=object_name, error=str(e))
        raise
