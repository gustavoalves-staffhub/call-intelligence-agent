"""Step 4: LLM extraction."""

import importlib
import json
from typing import Any

from pydantic import ValidationError

from app.config import get_settings
from app.models.note import ExtractedNote, GRSCallNote, IntakeCallNote, MedHubCallNote

_NOTE_MODELS: dict[str, type[ExtractedNote]] = {
    "intake": IntakeCallNote,
    "medhub": MedHubCallNote,
    "grs": GRSCallNote,
}


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

    raw_response = _response_text(response.content)
    try:
        raw_note = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Anthropic response was not valid strict JSON: {raw_response}"
        ) from exc

    if not isinstance(raw_note, dict):
        raise ValueError(f"Anthropic response JSON must be an object: {raw_response}")

    _normalize_callback_date(raw_note)
    _reject_unexpected_fields(raw_note, note_model, raw_response)

    try:
        return note_model.model_validate(raw_note)
    except ValidationError as exc:
        raise ValueError(
            f"Anthropic response did not match {note_model.__name__}: {raw_response}"
        ) from exc


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
