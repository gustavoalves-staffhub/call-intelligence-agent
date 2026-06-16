"""Structured note models produced by LLM extraction."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ExtractedNote(BaseModel):
    """Base extracted note shared by all CRM workspaces."""

    summary: str
    disposition: str
    next_steps: str | None
    callback_date: date | None
    sentiment: Literal["positive", "neutral", "negative"]
    objections: str | None
    pii_detected: bool
    confidence: float = Field(ge=0.0, le=1.0)


class IntakeCallNote(ExtractedNote):
    """Intake-specific extracted note fields."""

    injury_details: str | None
    case_type: str | None


class MedHubCallNote(ExtractedNote):
    """MedHub-specific extracted note fields."""

    patient_complaints: str | None
    procedures_mentioned: str | None


class GRSCallNote(ExtractedNote):
    """GRS-specific extracted note fields."""

    case_status: str | None
    documents_mentioned: str | None
