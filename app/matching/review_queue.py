"""Manual review queue integration."""

import httpx

from app.config import get_settings
from app.models.call_event import CallEvent


async def send_to_review(event: CallEvent, reason: str) -> None:
    """Send unmatched or low-confidence calls to the Slack review queue."""

    webhook_url = get_settings().pipeline.slack_review_queue_webhook_url
    if not webhook_url:
        raise RuntimeError("SLACK_REVIEW_QUEUE_WEBHOOK_URL must be configured for review queue.")

    text = (
        "Call Intelligence review needed\n"
        f"call_id: {event.call_id}\n"
        f"phone_from: {event.phone_from}\n"
        f"phone_to: {event.phone_to}\n"
        f"duration_sec: {event.duration_sec}\n"
        f"reason: {reason}"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(webhook_url, json={"text": text})
        response.raise_for_status()
