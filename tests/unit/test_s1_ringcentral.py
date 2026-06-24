"""Tests for source polling normalization."""

import pytest

from app.models.call_event import CallEvent, CallSource
from app.worker.steps import s1_ingest
from app.worker.steps.s1_ingest import (
    _MAX_UNPROCESSED_BATCH_SIZE,
    _PHONEBURNER_QUERY,
    _cap_candidate_batch,
    _filter_unprocessed,
    _is_ringcentral_connected_record,
    _ringcentral_record_to_event,
)


def test_ringcentral_record_maps_patient_to_phone_from() -> None:
    """MedHub outbound calls use the RingCentral `to` party as the patient phone."""

    event = _ringcentral_record_to_event(
        {
            "id": "rc-123",
            "result": "Call connected",
            "duration": 91,
            "direction": "Outbound",
            "from": {"phoneNumber": "+17865550100", "name": "MedHub Agent"},
            "to": {"phoneNumber": "+13055551234", "name": "Patient Name"},
            "recording": {
                "id": "rec-123",
                "contentUri": "https://platform.ringcentral.com/restapi/recording/rec-123",
            },
        }
    )

    assert event.call_id == "rc-123"
    assert event.source is CallSource.RINGCENTRAL
    assert event.workspace == "medhub"
    assert event.phone_from == "+13055551234"
    assert event.phone_to == "+17865550100"
    assert event.patient_phone_primary == "+13055551234"
    assert event.patient_phone_fallback == "+17865550100"
    assert event.agent_id == "MedHub Agent"
    assert event.gcs_audio_uri is None
    assert event.raw_payload["patient_phone_primary"] == "+13055551234"
    assert event.raw_payload["patient_phone_fallback"] == "+17865550100"
    assert event.raw_payload["recording_content_uri"].endswith("/rec-123")
    assert event.raw_payload["recording_id"] == "rec-123"
    assert event.raw_payload["from_name"] == "MedHub Agent"
    assert event.raw_payload["to_name"] == "Patient Name"


def test_ringcentral_filter_requires_connected_duration_and_recording() -> None:
    """Only connected calls meeting duration and recording requirements are processed."""

    record = {
        "result": "Call connected",
        "duration": 30,
        "recording": {"contentUri": "https://example.com/audio.mp3"},
    }

    assert _is_ringcentral_connected_record(record, min_duration_seconds=30)
    assert not _is_ringcentral_connected_record(
        {**record, "result": "No Answer"},
        min_duration_seconds=30,
    )
    assert not _is_ringcentral_connected_record(
        {**record, "duration": 29},
        min_duration_seconds=30,
    )
    assert not _is_ringcentral_connected_record(
        {**record, "recording": None},
        min_duration_seconds=30,
    )


def test_phoneburner_bigquery_polling_has_no_time_window() -> None:
    """PhoneBurner polling should rely on audit idempotency, not a time window."""

    assert "TIMESTAMP_SUB" not in _PHONEBURNER_QUERY
    assert "end_time >=" not in _PHONEBURNER_QUERY
    assert "connected = @connected" in _PHONEBURNER_QUERY
    assert "duration >= @min_duration_seconds" in _PHONEBURNER_QUERY
    assert "recording_gcs_uri IS NOT NULL" in _PHONEBURNER_QUERY
    assert "ORDER BY end_time ASC" in _PHONEBURNER_QUERY


def _call_event(index: int) -> CallEvent:
    """Build a minimal PhoneBurner event for polling tests."""

    return CallEvent(
        call_id=f"call-{index}",
        source=CallSource.PHONEBURNER,
        workspace="intake",
        phone_from="+15550000001",
        phone_to="+15550000002",
        duration_sec=60,
        agent_id=None,
        gcs_audio_uri="gs://bucket/audio.mp3",
        raw_payload={},
    )


def test_candidate_batch_cap_warns_and_limits_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Large candidate batches should be capped before Cloud SQL checks."""

    events = [_call_event(index) for index in range(_MAX_UNPROCESSED_BATCH_SIZE + 1)]

    with caplog.at_level("WARNING"):
        capped = _cap_candidate_batch(events)

    assert len(capped) == _MAX_UNPROCESSED_BATCH_SIZE
    assert capped[0].call_id == "call-0"
    assert capped[-1].call_id == f"call-{_MAX_UNPROCESSED_BATCH_SIZE - 1}"
    assert "exceeds batch cap" in caplog.text


async def test_filter_unprocessed_uses_batch_processed_call_id_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Idempotency filtering should use one batch lookup for all candidate IDs."""

    captured_call_ids: list[str] = []

    async def fake_processed_call_ids(call_ids: list[str]) -> set[str]:
        captured_call_ids.extend(call_ids)
        return {"call-1"}

    monkeypatch.setattr(s1_ingest, "processed_call_ids", fake_processed_call_ids)

    events = [_call_event(index) for index in range(3)]
    unprocessed = await _filter_unprocessed(events)

    assert captured_call_ids == ["call-0", "call-1", "call-2"]
    assert [event.call_id for event in unprocessed] == ["call-0", "call-2"]


async def test_poll_new_calls_caps_candidates_before_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 200-call cap should be applied before Cloud SQL idempotency checks."""

    captured_count = 0

    async def fake_poll_phoneburner() -> list[CallEvent]:
        return [
            _call_event(index)
            for index in range(_MAX_UNPROCESSED_BATCH_SIZE + 1)
        ]

    async def fake_poll_ringcentral_api() -> list[CallEvent]:
        return []

    async def fake_filter_unprocessed(events: list[CallEvent]) -> list[CallEvent]:
        nonlocal captured_count
        captured_count = len(events)
        return events

    monkeypatch.setattr(s1_ingest, "_poll_phoneburner", fake_poll_phoneburner)
    monkeypatch.setattr(s1_ingest, "_poll_ringcentral_api", fake_poll_ringcentral_api)
    monkeypatch.setattr(s1_ingest, "_filter_unprocessed", fake_filter_unprocessed)

    events = await s1_ingest.poll_new_calls()

    assert captured_count == _MAX_UNPROCESSED_BATCH_SIZE
    assert len(events) == _MAX_UNPROCESSED_BATCH_SIZE
