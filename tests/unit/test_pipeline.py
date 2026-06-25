"""Tests for pipeline terminal-state handling."""

import pytest

from app.models.call_event import CallEvent
from app.models.match_result import MatchMethod, MatchResult
from app.models.note import ExtractedNote
from app.worker import pipeline


async def test_manual_review_is_audited_without_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_call_event: CallEvent,
    mock_extracted_note: ExtractedNote,
) -> None:
    """Manual-review calls should be processed for idempotency, not error-looped."""

    captured_results: list[dict[str, object]] = []

    async def fake_check_idempotency(call_id: str) -> bool:
        _ = call_id
        return False

    async def fake_fetch_recording(event: CallEvent) -> CallEvent:
        return event

    async def fake_transcribe(event: CallEvent) -> str:
        _ = event
        return "[Agent]: hello\n[Lead]: hello"

    async def fake_extract(transcript: str, workspace: str) -> ExtractedNote:
        _ = transcript, workspace
        return mock_extracted_note

    async def fake_match_lead(
        event: CallEvent,
        crm_clients: object,
    ) -> MatchResult:
        _ = event, crm_clients
        return MatchResult(
            crm_record_id="lead-123",
            workspace="intake",
            confidence=0.7,
            method=MatchMethod.NAME,
            requires_review=True,
        )

    async def fake_log_result(
        event: CallEvent,
        match: MatchResult,
        note: ExtractedNote | None,
        error: str | None,
    ) -> None:
        captured_results.append(
            {
                "call_id": event.call_id,
                "requires_review": match.requires_review,
                "note": note,
                "error": error,
            }
        )

    monkeypatch.setattr(pipeline.s1_ingest, "check_idempotency", fake_check_idempotency)
    monkeypatch.setattr(pipeline.s2_fetch, "fetch_recording", fake_fetch_recording)
    monkeypatch.setattr(pipeline.s3_transcribe, "transcribe", fake_transcribe)
    monkeypatch.setattr(pipeline.s4_extract, "extract", fake_extract)
    monkeypatch.setattr(pipeline.s5_match, "match_lead", fake_match_lead)
    monkeypatch.setattr(pipeline.s8_audit, "log_result", fake_log_result)
    monkeypatch.setattr(pipeline, "get_crm_clients", lambda: {})

    with pytest.raises(pipeline.ManualReviewRequiredError):
        await pipeline.run(mock_call_event)

    assert captured_results == [
        {
            "call_id": "test-call-123",
            "requires_review": True,
            "note": mock_extracted_note,
            "error": None,
        }
    ]
