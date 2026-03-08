"""Firebase Authentication helpers."""

from __future__ import annotations

import json
import logging
import os

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

from app.config import settings

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def _init_firebase() -> firebase_admin.App | None:
    """Lazily initialise the Firebase Admin SDK.

    Priority order:
      1. ``FIREBASE_SERVICE_ACCOUNT_JSON`` env-var containing *inline* JSON.
      2. ``firebase_service_account`` setting (path to a JSON file on disk).
      3. ``GOOGLE_APPLICATION_CREDENTIALS`` env-var (standard GCP approach).

    Returns ``None`` when no credentials are available (Firebase auth will be
    disabled but the anonymous flow still works).
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    # Already initialised by another module / test
    if firebase_admin._apps:  # noqa: SLF001
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    cred = None

    # 1. Inline JSON from env var
    inline_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if inline_json:
        try:
            service_info = json.loads(inline_json)
            cred = credentials.Certificate(service_info)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: %s", exc)

    # 2. File path from settings
    if cred is None and settings.firebase_service_account:
        try:
            cred = credentials.Certificate(settings.firebase_service_account)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("Failed to load Firebase service account file: %s", exc)

    # 3. Default credentials (GOOGLE_APPLICATION_CREDENTIALS)
    if cred is None and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            cred = credentials.ApplicationDefault()
        except Exception as exc:
            logger.warning("Failed to load default application credentials: %s", exc)

    if cred is None:
        logger.info("Firebase credentials not configured — Firebase auth disabled")
        return None

    options: dict[str, str] = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id

    _firebase_app = firebase_admin.initialize_app(cred, options or None)
    logger.info("Firebase Admin SDK initialised")
    return _firebase_app


def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims.

    Returns a dict with at least ``uid``; may also contain ``email``,
    ``name``, ``picture``, ``email_verified``, etc.

    Raises ``ValueError`` when Firebase is not configured or the token is
    invalid / expired.
    """
    app = _init_firebase()
    if app is None:
        raise ValueError("Firebase is not configured on this server")

    try:
        decoded = firebase_auth.verify_id_token(id_token, app=app)
    except firebase_auth.InvalidIdTokenError as exc:
        raise ValueError(f"Invalid Firebase token: {exc}") from exc
    except firebase_auth.ExpiredIdTokenError as exc:
        raise ValueError(f"Expired Firebase token: {exc}") from exc
    except firebase_auth.RevokedIdTokenError as exc:
        raise ValueError(f"Revoked Firebase token: {exc}") from exc

    return decoded
