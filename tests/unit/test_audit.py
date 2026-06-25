"""Tests for audit log row construction."""

from typing import Any

from app.models.call_event import CallEvent, CallSource
from app.models.match_result import MatchMethod, MatchResult
from app.storage.audit import (
    DEEPGRAM_BAD_REQUEST_ERROR_MESSAGE,
    DEEPGRAM_NO_TRANSCRIPT_ERROR_MESSAGE,
)
from app.worker.steps import s8_audit


async def test_log_result_includes_matched_on_phone(monkeypatch: Any) -> None:
    """Audit rows should record which MedHub patient-phone candidate matched."""

    captured: dict[str, Any] = {}

    async def fake_upsert_call_log(row: dict[str, Any]) -> None:
        captured.update(row)

    monkeypatch.setattr(s8_audit, "upsert_call_log", fake_upsert_call_log)
    event = CallEvent(
        call_id="rc-123",
        source=CallSource.RINGCENTRAL,
        workspace="medhub",
        phone_from="+13055551234",
        phone_to="+17865550100",
        patient_phone_primary="+13055551234",
        patient_phone_fallback="+17865550100",
        duration_sec=60,
        agent_id="MedHub Agent",
        gcs_audio_uri="gs://bucket/audio.mp3",
        raw_payload={},
    )
    match = MatchResult(
        crm_record_id="lead-123",
        workspace="medhub",
        confidence=1.0,
        method=MatchMethod.PHONE,
        requires_review=False,
        matched_on_phone="fallback",
    )

    await s8_audit.log_result(event, match, note=None, error=None)

    assert captured["matched_on_phone"] == "fallback"


async def test_manual_review_log_result_is_processed_without_note(monkeypatch: Any) -> None:
    """Manual-review rows should satisfy idempotency without claiming a note write."""

    captured: dict[str, Any] = {}

    async def fake_upsert_call_log(row: dict[str, Any]) -> None:
        captured.update(row)

    monkeypatch.setattr(s8_audit, "upsert_call_log", fake_upsert_call_log)
    event = CallEvent(
        call_id="review-call",
        source=CallSource.PHONEBURNER,
        workspace="intake",
        phone_from="+15550000001",
        phone_to="+15550000002",
        duration_sec=60,
        agent_id=None,
        gcs_audio_uri="gs://bucket/audio.mp3",
        raw_payload={},
    )
    match = MatchResult(
        crm_record_id="lead-123",
        workspace="intake",
        confidence=0.7,
        method=MatchMethod.NAME,
        requires_review=True,
    )

    await s8_audit.log_result(event, match, note=None, error=None)

    assert captured["review_required"] is True
    assert captured["error_message"] is None
    assert captured["processed_at"] is not None
    assert captured["note_created"] is False


async def test_deepgram_no_transcript_error_is_processed_terminal_state(
    monkeypatch: Any,
) -> None:
    """No-transcript audio errors should not be retried forever."""

    captured: dict[str, Any] = {}

    async def fake_upsert_call_log(row: dict[str, Any]) -> None:
        captured.update(row)

    monkeypatch.setattr(s8_audit, "upsert_call_log", fake_upsert_call_log)
    event = CallEvent(
        call_id="silent-call",
        source=CallSource.PHONEBURNER,
        workspace="intake",
        phone_from="+15550000001",
        phone_to="+15550000002",
        duration_sec=60,
        agent_id=None,
        gcs_audio_uri="gs://bucket/audio.mp3",
        raw_payload={},
    )
    match = MatchResult(
        crm_record_id=None,
        workspace="intake",
        confidence=0.0,
        method=MatchMethod.UNMATCHED,
        requires_review=False,
    )

    await s8_audit.log_result(
        event,
        match,
        note=None,
        error=DEEPGRAM_NO_TRANSCRIPT_ERROR_MESSAGE,
    )

    assert captured["review_required"] is False
    assert captured["error_message"] == DEEPGRAM_NO_TRANSCRIPT_ERROR_MESSAGE
    assert captured["processed_at"] is not None
    assert captured["note_created"] is False


async def test_deepgram_bad_request_error_is_processed_terminal_state(
    monkeypatch: Any,
) -> None:
    """Corrupt or unsupported audio should not be retried forever."""

    captured: dict[str, Any] = {}

    async def fake_upsert_call_log(row: dict[str, Any]) -> None:
        captured.update(row)

    monkeypatch.setattr(s8_audit, "upsert_call_log", fake_upsert_call_log)
    event = CallEvent(
        call_id="corrupt-call",
        source=CallSource.PHONEBURNER,
        workspace="intake",
        phone_from="+15550000001",
        phone_to="+15550000002",
        duration_sec=60,
        agent_id=None,
        gcs_audio_uri="gs://bucket/audio.mp3",
        raw_payload={},
    )
    match = MatchResult(
        crm_record_id=None,
        workspace="intake",
        confidence=0.0,
        method=MatchMethod.UNMATCHED,
        requires_review=False,
    )

    await s8_audit.log_result(
        event,
        match,
        note=None,
        error=DEEPGRAM_BAD_REQUEST_ERROR_MESSAGE,
    )

    assert captured["review_required"] is False
    assert captured["error_message"] == DEEPGRAM_BAD_REQUEST_ERROR_MESSAGE
    assert captured["processed_at"] is not None
    assert captured["note_created"] is False
