"""RingCentral telephony adapter."""

from __future__ import annotations

from time import monotonic
from typing import Any, ClassVar

import httpx

from app.adapters.telephony.base import TelephonyAdapter
from app.config import get_settings

_PLATFORM_BASE_URL = "https://platform.ringcentral.com"
_TOKEN_URL = f"{_PLATFORM_BASE_URL}/restapi/oauth/token"
_TOKEN_EXPIRY_SKEW_SECONDS = 60.0


class RingCentralAdapter(TelephonyAdapter):
    """Adapter for RingCentral call logs, recordings, and metadata."""

    _cached_access_token: ClassVar[str | None] = None
    _cached_expires_at: ClassVar[float] = 0.0

    async def get_access_token(self) -> str:
        """Authenticate with RingCentral JWT grant and return a cached access token."""

        now = monotonic()
        if self._cached_access_token and now < self._cached_expires_at:
            return self._cached_access_token

        settings = get_settings().telephony.ringcentral
        if not settings.client_id:
            raise RuntimeError("RINGCENTRAL_CLIENT_ID must be configured.")
        if not settings.client_secret:
            raise RuntimeError("RINGCENTRAL_CLIENT_SECRET must be configured.")
        if not settings.jwt:
            raise RuntimeError("RINGCENTRAL_JWT must be configured.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _TOKEN_URL,
                auth=httpx.BasicAuth(settings.client_id, settings.client_secret),
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": settings.jwt,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

        payload = response.json()
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise RuntimeError("RingCentral token response did not include access_token.")

        expires_in = _int_value(payload.get("expires_in"), default=3600)
        self.__class__._cached_access_token = access_token.strip()
        self.__class__._cached_expires_at = now + max(
            0.0,
            float(expires_in) - _TOKEN_EXPIRY_SKEW_SECONDS,
        )
        return self.__class__._cached_access_token

    async def list_call_log(
        self,
        *,
        date_from: str,
        recording_type: str = "All",
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Return recent RingCentral call-log records for polling."""

        access_token = await self.get_access_token()
        url = f"{_PLATFORM_BASE_URL}/restapi/v1.0/account/{self._account_path()}/call-log"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url,
                params={
                    "recordingType": recording_type,
                    "dateFrom": date_from,
                    "perPage": per_page,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

        payload = response.json()
        records = payload.get("records")
        if not isinstance(records, list):
            return []
        return [record for record in records if isinstance(record, dict)]

    async def get_recording_bytes(self, content_uri: str, access_token: str | None = None) -> bytes:
        """Download RingCentral recording audio bytes from a contentUri."""

        uri = content_uri.strip()
        if not uri:
            raise ValueError("RingCentral recording content_uri is required.")

        token = access_token or await self.get_access_token()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                _absolute_url(uri),
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
        return response.content

    async def get_recording_uri(self, call_id: str) -> str:
        """Return the RingCentral recording contentUri for a call-log record."""

        metadata = await self.get_call_metadata(call_id)
        recording = metadata.get("recording")
        if not isinstance(recording, dict):
            raise ValueError(f"RingCentral call {call_id!r} does not include a recording.")

        content_uri = recording.get("contentUri")
        if not isinstance(content_uri, str) or not content_uri.strip():
            raise ValueError(f"RingCentral call {call_id!r} is missing recording contentUri.")
        return content_uri.strip()

    async def get_call_metadata(self, call_id: str) -> dict[str, Any]:
        """Fetch one RingCentral call-log record by id."""

        if not call_id.strip():
            raise ValueError("RingCentral call_id is required.")

        access_token = await self.get_access_token()
        url = (
            f"{_PLATFORM_BASE_URL}/restapi/v1.0/account/{self._account_path()}"
            f"/call-log/{call_id.strip()}"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("RingCentral call-log response was not a JSON object.")
        return payload

    def _account_path(self) -> str:
        """Return configured account id or RingCentral's current-account shortcut."""

        account_id = get_settings().telephony.ringcentral.account_id.strip()
        return account_id or "~"


def _absolute_url(uri: str) -> str:
    """Normalize RingCentral relative API paths to absolute URLs."""

    if uri.startswith("http://") or uri.startswith("https://"):
        return uri
    if uri.startswith("/"):
        return f"{_PLATFORM_BASE_URL}{uri}"
    return f"{_PLATFORM_BASE_URL}/{uri}"


def _int_value(value: Any, *, default: int) -> int:
    """Convert a provider numeric value to int with a safe default."""

    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
