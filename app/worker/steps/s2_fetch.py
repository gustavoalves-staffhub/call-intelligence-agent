"""Step 2: fetch or verify call recording."""

from app.adapters.telephony.phoneburner import PhoneBurnerAdapter
from app.config import get_settings
from app.models.call_event import CallEvent, CallSource
from app.storage.gcs import file_exists


async def fetch_recording(event: CallEvent) -> CallEvent:
    """Verify or fetch the recording for a call event."""

    settings = get_settings()
    if event.duration_sec < settings.pipeline.min_call_duration_seconds:
        raise ValueError("Call duration is below MIN_CALL_DURATION_SECONDS; skipping processing.")

    if event.gcs_audio_uri:
        if not await file_exists(event.gcs_audio_uri):
            raise FileNotFoundError(f"Call recording not found at {event.gcs_audio_uri}")
        return event

    if event.source is CallSource.PHONEBURNER:
        uri = await PhoneBurnerAdapter.from_config().get_recording_uri(event.call_id)
        if not await file_exists(uri):
            raise FileNotFoundError(f"PhoneBurner recording not found at {uri}")
        return event.model_copy(update={"gcs_audio_uri": uri})

    if event.source is CallSource.RINGCENTRAL:
        return await _download_ringcentral_recording(event)

    raise ValueError(f"Unsupported call source: {event.source}")


async def _download_ringcentral_recording(event: CallEvent) -> CallEvent:
    """# TODO: implement once RingCentral GCS bucket name is confirmed."""

    _ = event
    raise NotImplementedError(
        "RingCentral recording download is pending GCS bucket name and API details."
    )
