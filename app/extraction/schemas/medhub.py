"""MedHub extraction schema and pending CRM field map."""

from app.models.note import MedHubCallNote

FIELD_MAP: dict[str, str] = {
    "summary": "",  # TODO: map to Twenty Note body or field after schema analysis.
    "disposition": "",  # TODO: map to MedHub disposition field.
    "next_steps": "",  # TODO: map to MedHub next steps field.
    "callback_date": "",  # TODO: map to MedHub callback date field.
    "sentiment": "",  # TODO: confirm if sentiment is stored in Twenty.
    "objections": "",  # TODO: map to MedHub objections field.
    "patient_complaints": "",  # TODO: map to MedHub complaints field.
    "procedures_mentioned": "",  # TODO: map to MedHub procedures field.
}

__all__ = ["FIELD_MAP", "MedHubCallNote"]
