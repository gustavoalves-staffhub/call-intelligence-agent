"""Step 2: fetch or verify call recording."""

from app.adapters.telephony.ringcentral import RingCentralAdapter
from app.config import get_settings
from app.models.call_event import CallEvent, CallSource
from app.storage.gcs import file_exists, upload_bytes
from app.worker.steps.s1_ingest import _RINGCENTRAL_MIN_CALL_DURATION_SECONDS


async def fetch_recording(event: CallEvent) -> CallEvent:
    """Verify PhoneBurner audio or fetch RingCentral audio into GCS."""

    min_duration_seconds = _min_duration_seconds_for_event(event)
    if event.duration_sec < min_duration_seconds:
        raise ValueError(
            f"Call duration is below {min_duration_seconds} seconds; skipping processing."
        )

    if event.source is CallSource.PHONEBURNER:
        if not event.gcs_audio_uri:
            raise FileNotFoundError("PhoneBurner call is missing recording_gcs_uri from BigQuery.")
        if not await file_exists(event.gcs_audio_uri):
            raise FileNotFoundError(f"PhoneBurner recording not found at {event.gcs_audio_uri}")
        return event

    if event.source is CallSource.RINGCENTRAL:
        return await _fetch_ringcentral_recording(event)

    raise ValueError(f"Unsupported call source: {event.source}")


def _min_duration_seconds_for_event(event: CallEvent) -> int:
    """Return the source-specific minimum duration before recording fetch."""

    if event.source is CallSource.RINGCENTRAL:
        return _RINGCENTRAL_MIN_CALL_DURATION_SECONDS

    return get_settings().pipeline.min_call_duration_seconds


async def _fetch_ringcentral_recording(event: CallEvent) -> CallEvent:
    """Fetch RingCentral audio by contentUri, upload it to GCS, and return the updated event."""

    settings = get_settings()
    content_uri = event.raw_payload.get("recording_content_uri")
    if not isinstance(content_uri, str) or not content_uri.strip():
        raise ValueError("RingCentral call is missing recording_content_uri in raw_payload.")
    if not settings.gcs.ringcentral_bucket:
        raise RuntimeError("GCS_RINGCENTRAL_BUCKET must be configured to store RingCentral audio.")

    adapter = RingCentralAdapter()
    access_token = await adapter.get_access_token()
    audio_bytes = await adapter.get_recording_bytes(content_uri, access_token)

    destination_uri = f"gs://{settings.gcs.ringcentral_bucket}/{event.call_id}.mp3"
    uploaded_uri = await upload_bytes(
        audio_bytes,
        destination_uri,
        content_type="audio/mpeg",
    )
    return event.model_copy(update={"gcs_audio_uri": uploaded_uri})
