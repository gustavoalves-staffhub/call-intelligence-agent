"""Tests for recording fetch eligibility guards."""

from app.models.call_event import CallEvent, CallSource
from app.worker.steps.s1_ingest import _RINGCENTRAL_MIN_CALL_DURATION_SECONDS
from app.worker.steps.s2_fetch import _min_duration_seconds_for_event


def test_min_duration_is_source_specific() -> None:
    """RingCentral uses a shorter conversation threshold than PhoneBurner."""

    phoneburner_event = _event(CallSource.PHONEBURNER)
    ringcentral_event = _event(CallSource.RINGCENTRAL)

    assert _min_duration_seconds_for_event(phoneburner_event) == 30
    assert (
        _min_duration_seconds_for_event(ringcentral_event) == _RINGCENTRAL_MIN_CALL_DURATION_SECONDS
    )


def _event(source: CallSource) -> CallEvent:
    return CallEvent(
        call_id="call-1",
        source=source,
        workspace="medhub" if source is CallSource.RINGCENTRAL else "intake",
        phone_from="+15550000001",
        phone_to="+15550000002",
        duration_sec=15,
        agent_id=None,
        gcs_audio_uri="gs://bucket/audio.mp3",
        raw_payload={},
    )
