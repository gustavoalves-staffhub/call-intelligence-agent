"""Step 5: lead matching."""

from app.adapters.crm.factory import get_crm_clients
from app.config import get_settings
from app.matching.matcher import match
from app.models.call_event import CallEvent
from app.models.match_result import MatchResult
from app.models.note import ExtractedNote


async def match_lead(event: CallEvent, note: ExtractedNote) -> MatchResult:
    """Match a call to a CRM record by phone, then name, DOB, and email when available."""

    _ = note
    result = await match(event, get_crm_clients())
    threshold = get_settings().pipeline.match_confidence_threshold
    if result.confidence < threshold:
        return result.model_copy(update={"requires_review": True})
    return result
