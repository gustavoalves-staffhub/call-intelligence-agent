"""Step 1: ingest and idempotency checks."""

from app.storage.audit import is_processed


async def check_idempotency(call_id: str) -> bool:
    """Query call_audit_log and return True when call_id was already processed."""

    return await is_processed(call_id)
