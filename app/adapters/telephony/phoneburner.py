"""PhoneBurner telephony adapter."""

from typing import Any

from app.adapters.telephony.base import TelephonyAdapter
from app.config import get_settings


class PhoneBurnerAdapter(TelephonyAdapter):
    """Adapter for PhoneBurner recordings and metadata."""

    def __init__(self, api_key: str, audio_bucket: str) -> None:
        """Initialize the adapter with non-empty settings supplied by config."""

        self.api_key = api_key
        self.audio_bucket = audio_bucket

    @classmethod
    def from_config(cls) -> "PhoneBurnerAdapter":
        """Build a PhoneBurner adapter from application settings."""

        settings = get_settings()
        return cls(
            api_key=settings.telephony.phoneburner.api_key,
            audio_bucket=settings.gcs.audio_bucket,
        )

    async def get_recording_uri(self, call_id: str) -> str:
        """Construct the expected GCS URI for a PhoneBurner recording.

        TODO: confirm the exact PhoneBurner filename format. This placeholder
        assumes recordings are stored as `<call_id>.mp3` in the configured bucket.
        """

        return f"gs://{self.audio_bucket}/{call_id}.mp3"

    async def get_call_metadata(self, call_id: str) -> dict[str, Any]:
        """Fetch PhoneBurner REST API metadata for a call."""

        _ = call_id
        raise NotImplementedError(
            "PhoneBurner metadata lookup is pending API endpoint and response schema analysis."
        )
