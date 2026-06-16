"""RingCentral telephony adapter."""

from typing import Any

from app.adapters.telephony.base import TelephonyAdapter


class RingCentralAdapter(TelephonyAdapter):
    """Adapter for RingCentral recordings and metadata."""

    async def get_recording_uri(self, call_id: str) -> str:
        """# TODO: implement once RingCentral GCS bucket name and API credentials are confirmed."""

        _ = call_id
        raise NotImplementedError(
            "RingCentral recording URI lookup is pending bucket and credential confirmation."
        )

    async def get_call_metadata(self, call_id: str) -> dict[str, Any]:
        """# TODO: implement once RingCentral GCS bucket name and API credentials are confirmed."""

        _ = call_id
        raise NotImplementedError(
            "RingCentral metadata lookup is pending bucket and credential confirmation."
        )
