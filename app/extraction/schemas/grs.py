"""GRS extraction schema and pending CRM field map."""

from app.models.note import GRSCallNote

FIELD_MAP: dict[str, str] = {
    "summary": "",  # TODO: map to Twenty Note body or field after schema analysis.
    "disposition": "",  # TODO: map to GRS disposition field.
    "next_steps": "",  # TODO: map to GRS next steps field.
    "callback_date": "",  # TODO: map to GRS callback date field.
    "sentiment": "",  # TODO: confirm if sentiment is stored in Twenty.
    "objections": "",  # TODO: map to GRS objections field.
    "case_status": "",  # TODO: map to GRS case status field.
    "documents_mentioned": "",  # TODO: map to GRS documents field.
}

__all__ = ["FIELD_MAP", "GRSCallNote"]
