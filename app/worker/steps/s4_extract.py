"""Step 4: LLM extraction."""

from app.extraction.agent import extract_note
from app.models.note import ExtractedNote, GRSCallNote, IntakeCallNote, MedHubCallNote

_NOTE_MODELS: dict[str, type[ExtractedNote]] = {
    "intake": IntakeCallNote,
    "medhub": MedHubCallNote,
    "grs": GRSCallNote,
}


async def extract(transcript: str, workspace: str) -> ExtractedNote:
    """Extract a structured note and validate it against the workspace schema."""

    note_model = _NOTE_MODELS.get(workspace)
    if note_model is None:
        raise ValueError(f"Unsupported workspace for extraction: {workspace}")

    raw_note = await extract_note(transcript, workspace)
    return note_model.model_validate(raw_note)
