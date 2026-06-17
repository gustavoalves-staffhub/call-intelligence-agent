"""Twenty CRM client for the MedHub workspace."""

from app.adapters.crm.base import CallWriteResult
from app.adapters.crm.intake import IntakeCRMClient
from app.models.call_event import CallEvent
from app.models.note import ExtractedNote


class MedHubCRMClient(IntakeCRMClient):
    """Workspace-scoped Twenty GraphQL client for MedHub Leads.

    MedHub uses RingCentral rather than PhoneBurner, but the confirmed Twenty
    write flow is identical: createPhoneCall, createNote, createNoteTarget, then
    update native Lead fields.
    """

    async def write_call_note(
        self,
        *,
        lead_id: str,
        event: CallEvent,
        note: ExtractedNote,
        transcription: str,
        transcript_uri: str | None,
    ) -> CallWriteResult:
        """Create the MedHub call note using the shared Twenty write flow."""

        # HIPAA: transcripts must be encrypted at rest before MedHub goes live — pending BAA clearance
        return await super().write_call_note(
            lead_id=lead_id,
            event=event,
            note=note,
            transcription=transcription,
            transcript_uri=transcript_uri,
        )
