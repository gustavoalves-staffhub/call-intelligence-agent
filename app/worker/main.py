"""Worker Cloud Run entry point for Pub/Sub call processing."""

import asyncio
import logging

from google.cloud import pubsub_v1  # type: ignore[attr-defined]

from app.config import get_settings
from app.models.call_event import CallEvent
from app.worker import pipeline

logger = logging.getLogger(__name__)


async def process_message_data(data: bytes) -> None:
    """Deserialize a Pub/Sub message body and run the pipeline."""

    event = CallEvent.model_validate_json(data)
    await pipeline.run(event)


def _callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """Ack on pipeline success and nack on pipeline failure."""

    try:
        asyncio.run(process_message_data(message.data))
    except Exception:
        logger.exception("Call Intelligence worker failed to process Pub/Sub message.")
        message.nack()
    else:
        message.ack()


def main() -> None:
    """Start a Pub/Sub subscriber loop for the worker service."""

    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.gcp.project_id:
        raise RuntimeError("GCP_PROJECT_ID must be configured for the worker.")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        settings.gcp.project_id,
        settings.gcp.pubsub_subscription_worker,
    )

    streaming_pull = subscriber.subscribe(subscription_path, callback=_callback)
    logger.info("Worker listening on subscription %s", subscription_path)

    try:
        streaming_pull.result()
    except KeyboardInterrupt:
        streaming_pull.cancel()
        streaming_pull.result()


if __name__ == "__main__":
    main()
