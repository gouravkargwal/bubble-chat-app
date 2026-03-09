"""Google Play Developer API client for subscription verification."""

import json

import httpx
import structlog
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from app.config import settings

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]
BASE_URL = "https://androidpublisher.googleapis.com/androidpublisher/v3"


class GooglePlayClient:
    """Verifies Google Play subscription purchases."""

    def __init__(self) -> None:
        self._credentials: service_account.Credentials | None = None

    def _get_credentials(self) -> service_account.Credentials:
        if self._credentials is None or not self._credentials.valid:
            sa_path = settings.google_play_service_account
            if not sa_path:
                raise ValueError("Google Play service account not configured")

            self._credentials = service_account.Credentials.from_service_account_file(
                sa_path, scopes=SCOPES
            )

        if self._credentials.expired:
            self._credentials.refresh(Request())

        return self._credentials

    async def verify_subscription(
        self, product_id: str, purchase_token: str
    ) -> dict | None:
        """Verify a subscription purchase with Google Play.

        Returns the subscription resource dict if valid, None if invalid.
        """
        creds = self._get_credentials()
        package_name = settings.google_play_package_name

        url = (
            f"{BASE_URL}/applications/{package_name}"
            f"/purchases/subscriptionsv2/tokens/{purchase_token}"
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {creds.token}"},
                timeout=15.0,
            )

        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                "play_subscription_verified",
                product_id=product_id,
                state=data.get("subscriptionState"),
            )
            return data

        logger.warning(
            "play_subscription_verification_failed",
            status=resp.status_code,
            body=resp.text[:500],
        )
        return None

    async def acknowledge_subscription(
        self, product_id: str, purchase_token: str
    ) -> bool:
        """Acknowledge a subscription purchase."""
        creds = self._get_credentials()
        package_name = settings.google_play_package_name

        url = (
            f"{BASE_URL}/applications/{package_name}"
            f"/purchases/subscriptions/{product_id}"
            f"/tokens/{purchase_token}:acknowledge"
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {creds.token}"},
                timeout=15.0,
            )

        return resp.status_code == 204


# Singleton
_client: GooglePlayClient | None = None


def get_play_client() -> GooglePlayClient:
    global _client
    if _client is None:
        _client = GooglePlayClient()
    return _client
