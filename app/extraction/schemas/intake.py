"""Intake extraction schema and pending CRM field map."""

from app.models.note import IntakeCallNote

FIELD_MAP: dict[str, str] = {
    "summary": "",  # TODO: map to Twenty Note body or field after schema analysis.
    "disposition": "",  # TODO: map to Intake disposition field.
    "next_steps": "",  # TODO: map to Intake next steps field.
    "callback_date": "",  # TODO: map to Intake callback date field.
    "sentiment": "",  # TODO: confirm if sentiment is stored in Twenty.
    "objections": "",  # TODO: map to Intake objections field.
    "injury_details": "",  # TODO: map to Intake injury details field.
    "case_type": "",  # TODO: map to Intake case type field.
}

__all__ = ["FIELD_MAP", "IntakeCallNote"]
