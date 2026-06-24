"""Twenty CRM client for the MedHub workspace."""

import logging
from typing import Any

from app.adapters.crm.base import CallWriteResult
from app.adapters.crm.intake import IntakeCRMClient
from app.models.call_event import CallEvent
from app.models.note import ExtractedNote

logger = logging.getLogger(__name__)

_MEDHUB_LEAD_NODE_FIELDS = """
id
name { firstName lastName }
emails { primaryEmail }
phones { primaryPhoneNumber }
birthDate
contactAttemptCount
"""


class MedHubCRMClient(IntakeCRMClient):
    """Workspace-scoped Twenty GraphQL client for MedHub Leads.

    MedHub uses RingCentral rather than PhoneBurner, but the confirmed Twenty
    write flow is identical: createPhoneCall, createNote, createNoteTarget, then
    update native Lead fields.
    """

    async def find_record_by_phone(
        self,
        phone: str,
        fallback_phone: str | None = None,
    ) -> dict[str, Any] | None:
        """Find a MedHub Lead by primary and fallback patient phone candidates.

        MedHub stores primaryPhoneCallingCode as an empty string, so matching on
        the calling code would miss valid Leads. The shared normalizer still
        strips +1 and other punctuation before each query runs.
        """

        seen_numbers: set[str] = set()
        for label, candidate in (("primary", phone), ("fallback", fallback_phone)):
            normalized_number = self._normalize_medhub_phone_number(candidate)
            if not normalized_number or normalized_number in seen_numbers:
                continue
            seen_numbers.add(normalized_number)

            logger.info(
                "MedHub phone lookup: querying primaryPhoneNumber='%s'", normalized_number
            )
            record = await self._find_record_by_primary_phone_number(normalized_number)
            if record:
                return {**record, "_matched_on_phone": label}

        return None

    async def _find_record_by_primary_phone_number(
        self,
        phone_number: str,
    ) -> dict[str, Any] | None:
        """Find one MedHub Lead by phones.primaryPhoneNumber only."""

        query = f"""
          query FindMedHubLeadByPhone($phoneNumber: String!) {{
            leads(filter: {{
              phones: {{
                primaryPhoneNumber: {{ eq: $phoneNumber }}
              }}
            }}) {{
              edges {{ node {{ {_MEDHUB_LEAD_NODE_FIELDS} }} }}
            }}
          }}
        """
        data = await self.gql_request(
            query,
            {
                "phoneNumber": phone_number,
            },
        )
        return self.first_edge_node(data.get("leads"))

    def _normalize_medhub_phone_number(self, phone: str | None) -> str | None:
        """Normalize a MedHub patient phone candidate to the stored 10-digit number."""

        if not phone:
            return None
        try:
            return self.normalize_phone(phone).number
        except ValueError:
            return None

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
