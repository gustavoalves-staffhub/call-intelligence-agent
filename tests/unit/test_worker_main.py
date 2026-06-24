"""Tests for worker polling loop behavior."""

import pytest

from app.adapters.crm.base import TwentyCRMError
from app.models.call_event import CallEvent, CallSource
from app.worker import main, pipeline


def _event(call_id: str) -> CallEvent:
    """Build a minimal call event for worker-loop tests."""

    return CallEvent(
        call_id=call_id,
        source=CallSource.PHONEBURNER,
        workspace="intake",
        phone_from="+15550000001",
        phone_to="+15550000002",
        duration_sec=60,
        agent_id=None,
        gcs_audio_uri="gs://bucket/audio.mp3",
        raw_payload={},
    )


async def test_process_polled_calls_continues_after_manual_review(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Manual-review calls should not make the worker exit non-zero."""

    events = [_event("review-call"), _event("next-call")]
    processed: list[str] = []

    async def fake_poll_new_calls() -> list[CallEvent]:
        return events

    async def fake_pipeline_run(event: CallEvent) -> None:
        processed.append(event.call_id)
        if event.call_id == "review-call":
            raise pipeline.ManualReviewRequiredError(pipeline.MANUAL_REVIEW_ERROR_MESSAGE)

    monkeypatch.setattr(main, "poll_new_calls", fake_poll_new_calls)
    monkeypatch.setattr(main.pipeline, "run", fake_pipeline_run)

    with caplog.at_level("WARNING"):
        await main.process_polled_calls()

    assert processed == ["review-call", "next-call"]
    assert "call_id=review-call" in caplog.text
    assert pipeline.MANUAL_REVIEW_ERROR_MESSAGE in caplog.text


async def test_process_polled_calls_continues_after_twenty_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Twenty rate limits should not make the worker exit non-zero."""

    events = [_event("rate-limited-call"), _event("next-call")]
    processed: list[str] = []

    async def fake_poll_new_calls() -> list[CallEvent]:
        return events

    async def fake_pipeline_run(event: CallEvent) -> None:
        processed.append(event.call_id)
        if event.call_id == "rate-limited-call":
            raise TwentyCRMError(
                "Limit reached: token rate exceeded",
                code="BAD_USER_INPUT",
            )

    monkeypatch.setattr(main, "poll_new_calls", fake_poll_new_calls)
    monkeypatch.setattr(main.pipeline, "run", fake_pipeline_run)

    with caplog.at_level("WARNING"):
        await main.process_polled_calls()

    assert processed == ["rate-limited-call", "next-call"]
    assert "call_id=rate-limited-call" in caplog.text
    assert "Limit reached" in caplog.text
