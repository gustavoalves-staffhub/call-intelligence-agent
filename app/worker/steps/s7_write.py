"""Step 7: write extracted notes and fields to CRM."""

from app.adapters.crm.factory import get_crm_clients
from app.models.call_event import CallEvent
from app.models.match_result import MatchResult
from app.models.note import ExtractedNote


async def write_note(
    match: MatchResult,
    note: ExtractedNote,
    event: CallEvent,
    transcription: str,
) -> None:
    """Write a note and update fields on the matched CRM record."""

    if not match.crm_record_id:
        raise ValueError("Cannot write CRM note without crm_record_id.")
    if match.requires_review:
        raise ValueError("Cannot write CRM note for a match requiring manual review.")

    workspace = match.workspace or event.workspace
    client = get_crm_clients().get(workspace)
    if client is None:
        raise ValueError(f"No CRM client configured for workspace {workspace!r}.")

    await client.write_call_note(
        lead_id=match.crm_record_id,
        event=event,
        note=note,
        transcription=transcription,
        transcript_uri=_transcript_uri(event),
    )


def _transcript_uri(event: CallEvent) -> str | None:
    """Read an optional GCS transcript URI from webhook metadata."""

    for key in ("gcs_transcript_uri", "transcript_uri", "transcriptGcsUri"):
        value = event.raw_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
