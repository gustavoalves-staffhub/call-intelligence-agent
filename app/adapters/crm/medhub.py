"""Twenty CRM client stub for the MedHub workspace."""

from datetime import date
from typing import Any

from app.adapters.crm.base import CallWriteResult, CRMClient
from app.models.call_event import CallEvent
from app.models.note import ExtractedNote

CRM_PENDING_DOC = """# TODO: implement after Twenty CRM GraphQL schema analysis is complete.
# Required info:
# - Note creation mutation (Prompt A)
# - Phone query structure (Prompt B)
# - Auth header format and token (Prompt C)
# - Custom fields for disposition/next_steps/callback_date (Prompt D)
"""


class MedHubCRMClient(CRMClient):
    """Twenty CRM client for MedHub."""

    def __init__(self, base_url: str, api_token: str) -> None:
        """Store pending CRM connection settings without using them yet."""

        self.base_url = base_url
        self.api_token = api_token

    async def find_record_by_phone(self, phone: str) -> dict[str, Any] | None:
        """# TODO: implement after Twenty CRM GraphQL schema analysis is complete.
        # Required info:
        # - Note creation mutation (Prompt A)
        # - Phone query structure (Prompt B)
        # - Auth header format and token (Prompt C)
        # - Custom fields for disposition/next_steps/callback_date (Prompt D)
        """

        _ = phone
        raise NotImplementedError(CRM_PENDING_DOC)

    async def find_record_by_name(self, name: str) -> list[dict[str, Any]]:
        """# TODO: implement after Twenty CRM GraphQL schema analysis is complete.
        # Required info:
        # - Note creation mutation (Prompt A)
        # - Phone query structure (Prompt B)
        # - Auth header format and token (Prompt C)
        # - Custom fields for disposition/next_steps/callback_date (Prompt D)
        """

        _ = name
        raise NotImplementedError(CRM_PENDING_DOC)

    async def find_record_by_email(self, email: str) -> dict[str, Any] | None:
        """# TODO: implement after Twenty CRM GraphQL schema analysis is complete."""

        _ = email
        raise NotImplementedError(CRM_PENDING_DOC)

    async def find_records_by_birth_date(self, birth_date: date) -> list[dict[str, Any]]:
        """# TODO: implement after Twenty CRM GraphQL schema analysis is complete."""

        _ = birth_date
        raise NotImplementedError(CRM_PENDING_DOC)

    async def write_call_note(
        self,
        *,
        lead_id: str,
        event: CallEvent,
        note: ExtractedNote,
        transcription: str,
        transcript_uri: str | None,
    ) -> CallWriteResult:
        """# TODO: implement after Twenty CRM GraphQL schema analysis is complete."""

        _ = lead_id, event, note, transcription, transcript_uri
        raise NotImplementedError(CRM_PENDING_DOC)

    async def create_note(self, record_id: str, content: str, transcript_uri: str) -> str:
        """# TODO: implement after Twenty CRM GraphQL schema analysis is complete.
        # Required info:
        # - Note creation mutation (Prompt A)
        # - Phone query structure (Prompt B)
        # - Auth header format and token (Prompt C)
        # - Custom fields for disposition/next_steps/callback_date (Prompt D)
        """

        _ = record_id, content, transcript_uri
        raise NotImplementedError(CRM_PENDING_DOC)

    async def update_fields(self, record_id: str, fields: dict[str, Any]) -> None:
        """# TODO: implement after Twenty CRM GraphQL schema analysis is complete.
        # Required info:
        # - Note creation mutation (Prompt A)
        # - Phone query structure (Prompt B)
        # - Auth header format and token (Prompt C)
        # - Custom fields for disposition/next_steps/callback_date (Prompt D)
        """

        _ = record_id, fields
        raise NotImplementedError(CRM_PENDING_DOC)
