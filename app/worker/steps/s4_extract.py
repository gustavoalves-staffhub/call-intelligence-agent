"""Step 4: LLM extraction."""

import importlib
import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.config import get_settings
from app.models.note import ExtractedNote, GRSCallNote, IntakeCallNote, MedHubCallNote

_NOTE_MODELS: dict[str, type[ExtractedNote]] = {
    "intake": IntakeCallNote,
    "medhub": MedHubCallNote,
    "grs": GRSCallNote,
}
logger = logging.getLogger(__name__)


async def extract(transcript: str, workspace: str) -> ExtractedNote:
    """Extract a structured note from a transcript and validate it strictly."""

    note_model = _NOTE_MODELS.get(workspace)
    if note_model is None:
        raise ValueError(f"Unsupported workspace for extraction: {workspace}")

    from anthropic import AsyncAnthropicVertex

    settings = get_settings()
    if not settings.gcp.project_id:
        raise RuntimeError("GCP_PROJECT_ID must be configured before Vertex extraction.")

    prompt_module = importlib.import_module(f"app.extraction.prompts.{workspace}")
    system_prompt = str(getattr(prompt_module, "SYSTEM_PROMPT"))

    client = AsyncAnthropicVertex(
        region=settings.gcp.vertex_region,
        project_id=settings.gcp.project_id,
    )
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract one strict JSON object matching the workspace note schema. "
                    "Return JSON only, with no markdown or explanatory text.\n\n"
                    f"Transcript:\n{transcript}"
                ),
            }
        ],
    )

    return _parse_note_or_default(
        raw_response=_response_text(response.content),
        note_model=note_model,
        workspace=workspace,
    )


def _parse_note_or_default(
    *,
    raw_response: str,
    note_model: type[ExtractedNote],
    workspace: str,
) -> ExtractedNote:
    """Parse Claude JSON, falling back to a minimal note for unusable responses."""

    raw = raw_response.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()

    try:
        raw_note = json.loads(raw)
        if not isinstance(raw_note, dict):
            raise ValueError("Anthropic response JSON must be an object.")

        _normalize_callback_date(raw_note)
        _reject_unexpected_fields(raw_note, note_model, raw_response)
        return note_model.model_validate(raw_note)
    except (json.JSONDecodeError, ValueError, ValidationError) as exc:
        logger.warning(
            "Claude extraction response was not usable; returning default note. "
            "workspace=%s reason=%s",
            workspace,
            exc,
        )
        return _default_note(note_model)


def _default_note(note_model: type[ExtractedNote]) -> ExtractedNote:
    """Return a schema-valid fallback note for too-short or unusable transcripts."""

    raw_note: dict[str, Any] = {
        "summary": "Transcript too short to extract meaningful information.",
        "disposition": "No Answer",
        "next_steps": None,
        "callback_date": None,
        "sentiment": "neutral",
        "objections": None,
        "pii_detected": False,
        "confidence": 0.0,
    }

    for field_name in note_model.model_fields:
        raw_note.setdefault(field_name, None)

    return note_model.model_validate(raw_note)


def _response_text(content_blocks: Any) -> str:
    """Join text blocks returned by the Anthropic SDK."""

    parts: list[str] = []
    for block in content_blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
            continue

        if isinstance(block, dict):
            dict_text = block.get("text")
            if isinstance(dict_text, str):
                parts.append(dict_text)

    return "".join(parts).strip()


def _normalize_callback_date(raw_note: dict[str, Any]) -> None:
    """Keep callback_date compatible with the current date-only note model."""

    callback_date = raw_note.get("callback_date")
    if isinstance(callback_date, str) and "T" in callback_date:
        raw_note["callback_date"] = callback_date.split("T", maxsplit=1)[0]


def _reject_unexpected_fields(
    raw_note: dict[str, Any],
    note_model: type[ExtractedNote],
    raw_response: str,
) -> None:
    """Reject fields outside the selected workspace note schema."""

    expected_fields = set(note_model.model_fields)
    unexpected_fields = set(raw_note) - expected_fields
    if unexpected_fields:
        raise ValueError(
            "Anthropic response included fields outside "
            f"{note_model.__name__}: {sorted(unexpected_fields)}. Raw: {raw_response}"
        )
