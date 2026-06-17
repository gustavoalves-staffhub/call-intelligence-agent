"""Worker Cloud Run entry point for BigQuery-polled call processing."""

import asyncio
import logging

from app.worker import pipeline
from app.worker.steps.s1_ingest import poll_new_calls

logger = logging.getLogger(__name__)


async def process_polled_calls() -> None:
    """Poll BigQuery once and run the pipeline for each unprocessed call."""

    events = await poll_new_calls()
    logger.info("BigQuery polling found %d unprocessed call(s).", len(events))

    for event in events:
        await pipeline.run(event)


def main() -> None:
    """Run one BigQuery polling cycle for Cloud Run Jobs or scheduled invocations."""

    logging.basicConfig(level=logging.INFO)
    asyncio.run(process_polled_calls())


if __name__ == "__main__":
    main()
