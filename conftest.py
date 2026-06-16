"""Shared pytest fixtures for the Call Intelligence skeleton."""

import pytest

from app.models.call_event import CallEvent, CallSource
from app.models.match_result import MatchMethod, MatchResult
from app.models.note import IntakeCallNote


@pytest.fixture
def mock_call_event() -> CallEvent:
    """Return a valid CallEvent fixture without real PII."""

    return CallEvent(
        call_id="test-call-123",
        source=CallSource.PHONEBURNER,
        workspace="intake",
        phone_from="+15550000001",
        phone_to="+15550000002",
        duration_sec=120,
        agent_id="agent-1",
        gcs_audio_uri="gs://pb-dispositions-call-recordings/test-call-123.mp3",
        raw_payload={"name": "Test Lead"},
    )


@pytest.fixture
def mock_match_result() -> MatchResult:
    """Return a confident CRM match fixture."""

    return MatchResult(
        crm_record_id="crm-record-123",
        workspace="intake",
        confidence=1.0,
        method=MatchMethod.PHONE,
        requires_review=False,
    )


@pytest.fixture
def mock_extracted_note() -> IntakeCallNote:
    """Return a valid extracted note fixture."""

    return IntakeCallNote(
        summary="Lead discussed intake details.",
        disposition="Callback",
        next_steps="Follow up with intake packet.",
        callback_date=None,
        sentiment="neutral",
        objections="no data",
        pii_detected=False,
        confidence=0.9,
        injury_details="no data",
        case_type="no data",
    )
