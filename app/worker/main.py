"""Worker Cloud Run entry point for BigQuery-polled call processing."""

import asyncio
import logging

from deepgram.errors.bad_request_error import BadRequestError
from google.auth import default as google_auth_default
from google.auth.transport.requests import AuthorizedSession

from app.adapters.crm.base import TwentyCRMError, is_twenty_rate_limit_error
from app.adapters.stt.deepgram import DeepgramCreditsExhaustedError
from app.models.call_event import CallEvent
from app.models.match_result import MatchMethod, MatchResult
from app.storage.audit import (
    DEEPGRAM_BAD_REQUEST_ERROR_MESSAGE,
    DEEPGRAM_NO_TRANSCRIPT_ERROR_MESSAGE,
)
from app.worker import pipeline
from app.worker.steps.s1_ingest import poll_new_calls
from app.worker.steps.s8_audit import log_result

logger = logging.getLogger(__name__)

_SCHEDULER_PROJECT_ID = "keep-calm-database"
_SCHEDULER_REGION = "us-central1"
_SCHEDULER_JOB_ID = "call-intelligence-worker-scheduler"
_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_CLOUD_SCHEDULER_API_BASE_URL = "https://cloudscheduler.googleapis.com/v1"


async def process_polled_calls() -> None:
    """Poll BigQuery once and run the pipeline for each unprocessed call."""

    events = await poll_new_calls()
    logger.info("BigQuery polling found %d unprocessed call(s).", len(events))

    for event in events:
        try:
            await pipeline.run(event)
        except pipeline.ManualReviewRequiredError as exc:
            logger.warning(
                "Call requires manual review; continuing to next event. call_id=%s reason=%s",
                event.call_id,
                exc,
            )
            continue
        except TwentyCRMError as exc:
            if not is_twenty_rate_limit_error(exc):
                raise

            logger.warning(
                "Twenty CRM rate limit reached; continuing to next event. call_id=%s reason=%s",
                event.call_id,
                exc,
            )
            continue
        except BadRequestError as exc:
            logger.warning(
                "Deepgram bad request; continuing to next event. call_id=%s reason=%s",
                event.call_id,
                exc,
            )
            await _log_terminal_deepgram_error(
                event,
                DEEPGRAM_BAD_REQUEST_ERROR_MESSAGE,
            )
            continue
        except ValueError as exc:
            if not _is_deepgram_no_transcript_error(exc):
                raise

            logger.warning(
                "Deepgram returned no transcript; continuing to next event. call_id=%s reason=%s",
                event.call_id,
                exc,
            )
            await _log_terminal_deepgram_error(
                event,
                DEEPGRAM_NO_TRANSCRIPT_ERROR_MESSAGE,
            )
            continue


def _is_deepgram_no_transcript_error(error: ValueError) -> bool:
    """Return True for Deepgram responses that contain no transcript text."""

    return str(error).startswith("Deepgram response did not include a transcript")


async def _log_terminal_deepgram_error(event: CallEvent, error_message: str) -> None:
    """Write a terminal Deepgram failure row to the audit log."""

    await log_result(
        event,
        MatchResult(
            crm_record_id=None,
            workspace=event.workspace,
            confidence=0.0,
            method=MatchMethod.UNMATCHED,
            requires_review=False,
        ),
        note=None,
        error=error_message,
    )


def _pause_call_intelligence_worker_scheduler() -> None:
    """Pause the Cloud Scheduler job that invokes the worker."""

    credentials, _ = google_auth_default(scopes=[_CLOUD_PLATFORM_SCOPE])
    session = AuthorizedSession(credentials)
    job_name = (
        f"projects/{_SCHEDULER_PROJECT_ID}/locations/{_SCHEDULER_REGION}/jobs/{_SCHEDULER_JOB_ID}"
    )
    response = session.post(
        f"{_CLOUD_SCHEDULER_API_BASE_URL}/{job_name}:pause",
        timeout=30,
    )
    response.raise_for_status()
    logger.info("Paused Cloud Scheduler job %s.", job_name)


def main() -> int:
    """Run one BigQuery polling cycle for Cloud Run Jobs or scheduled invocations."""

    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(process_polled_calls())
    except DeepgramCreditsExhaustedError:
        logger.critical("Deepgram credits exhausted — pausing Cloud Scheduler and stopping worker")
        try:
            _pause_call_intelligence_worker_scheduler()
        except Exception:
            logger.exception(
                "Failed to pause Cloud Scheduler job after Deepgram credits exhaustion."
            )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
