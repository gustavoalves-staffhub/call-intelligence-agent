"""Worker Cloud Run entry point for BigQuery-polled call processing."""

import asyncio
import logging

from app.adapters.crm.base import TwentyCRMError, is_twenty_rate_limit_error
from app.worker import pipeline
from app.worker.steps.s1_ingest import poll_new_calls

logger = logging.getLogger(__name__)


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
                "Twenty CRM rate limit reached; continuing to next event. "
                "call_id=%s reason=%s",
                event.call_id,
                exc,
            )
            continue


def main() -> None:
    """Run one BigQuery polling cycle for Cloud Run Jobs or scheduled invocations."""

    logging.basicConfig(level=logging.INFO)
    asyncio.run(process_polled_calls())


if __name__ == "__main__":
    main()
