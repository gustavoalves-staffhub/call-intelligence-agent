"""Anthropic-backed note extraction helper."""

import importlib
import json
from typing import Any

from app.config import get_settings

_SUPPORTED_WORKSPACES = {"intake", "medhub", "grs"}


async def extract_note(transcript: str, workspace: str) -> dict[str, Any]:
    """Extract structured note JSON from a transcript using Anthropic."""

    if workspace not in _SUPPORTED_WORKSPACES:
        raise ValueError(f"Unsupported workspace for extraction: {workspace}")

    from anthropic import AsyncAnthropic

    prompt_module = importlib.import_module(f"app.extraction.prompts.{workspace}")
    system_prompt = str(getattr(prompt_module, "SYSTEM_PROMPT"))
    settings = get_settings()
    if not settings.llm.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY must be configured before extraction.")

    client = AsyncAnthropic(api_key=settings.llm.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the structured note JSON from this transcript.\n\n"
                    f"{transcript}"
                ),
            }
        ],
    )

    text = _response_text(response.content)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Anthropic response was not valid strict JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Anthropic response JSON must be an object.")
    return parsed


def _response_text(content_blocks: Any) -> str:
    """Join text blocks returned by the Anthropic SDK."""

    parts: list[str] = []
    for block in content_blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts).strip()
