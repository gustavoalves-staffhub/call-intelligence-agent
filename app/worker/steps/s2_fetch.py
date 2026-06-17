"""Step 2: fetch or verify call recording."""

import httpx

from app.config import get_settings
from app.models.call_event import CallEvent, CallSource
from app.storage.gcs import file_exists, upload_bytes


async def fetch_recording(event: CallEvent) -> CallEvent:
    """Verify PhoneBurner audio or fetch RingCentral audio into GCS."""

    settings = get_settings()
    if event.duration_sec < settings.pipeline.min_call_duration_seconds:
        raise ValueError("Call duration is below MIN_CALL_DURATION_SECONDS; skipping processing.")

    if event.source is CallSource.PHONEBURNER:
        if not event.gcs_audio_uri:
            raise FileNotFoundError("PhoneBurner call is missing recording_gcs_uri from BigQuery.")
        if not await file_exists(event.gcs_audio_uri):
            raise FileNotFoundError(f"PhoneBurner recording not found at {event.gcs_audio_uri}")
        return event

    if event.source is CallSource.RINGCENTRAL:
        return await _fetch_ringcentral_recording(event)

    raise ValueError(f"Unsupported call source: {event.source}")


async def _fetch_ringcentral_recording(event: CallEvent) -> CallEvent:
    """Fetch RingCentral audio by record_uri, upload it to GCS, and return the updated event."""

    settings = get_settings()
    record_uri = event.raw_payload.get("record_uri")
    if not isinstance(record_uri, str) or not record_uri.strip():
        raise ValueError("RingCentral call is missing record_uri in raw_payload.")
    if not settings.telephony.ringcentral.access_token:
        raise RuntimeError("RINGCENTRAL_ACCESS_TOKEN must be configured to fetch call audio.")
    if not settings.gcs.ringcentral_bucket:
        raise RuntimeError("GCS_RINGCENTRAL_BUCKET must be configured to store RingCentral audio.")

    # TODO: implement token refresh flow — RingCentral access tokens expire, refresh needed for production
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            record_uri,
            headers={"Authorization": f"Bearer {settings.telephony.ringcentral.access_token}"},
        )
        response.raise_for_status()

    destination_uri = f"gs://{settings.gcs.ringcentral_bucket}/{event.call_id}.mp3"
    uploaded_uri = await upload_bytes(
        response.content,
        destination_uri,
        content_type=response.headers.get("content-type", "audio/mpeg"),
    )
    return event.model_copy(update={"gcs_audio_uri": uploaded_uri})
