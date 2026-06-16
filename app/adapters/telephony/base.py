"""Base protocol for telephony provider adapters."""

from typing import Any, Protocol


class TelephonyAdapter(Protocol):
    """Interface required for telephony integrations."""

    async def get_recording_uri(self, call_id: str) -> str:
        """Return a GCS URI or provider URI for a call recording."""
        ...

    async def get_call_metadata(self, call_id: str) -> dict[str, Any]:
        """Return provider metadata needed to normalize a call event."""
        ...
