"""Tests for audit log row construction."""

from typing import Any

from app.models.call_event import CallEvent, CallSource
from app.models.match_result import MatchMethod, MatchResult
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
