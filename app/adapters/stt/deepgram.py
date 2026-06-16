"""Deepgram speech-to-text adapter."""

from typing import Any

import httpx

from app.adapters.stt.base import STTAdapter


class DeepgramAdapter(STTAdapter):
    """Deepgram REST API adapter using the nova-2-phonecall model."""

    supports_diarization = True
    supports_language_detection = True

    def __init__(self, api_key: str) -> None:
        """Initialize the adapter with a Deepgram API key."""

        self.api_key = api_key

    async def transcribe(self, gcs_uri: str) -> str:
        """Transcribe a GCS-hosted audio URI with Deepgram.

        TODO: confirm whether production should use signed GCS URLs. Deepgram
        generally needs a URL it can fetch, so raw `gs://` URIs may need to be
        exchanged for signed HTTPS URLs before this method is production-ready.
        """

        if not self.api_key:
            raise RuntimeError("DEEPGRAM_API_KEY must be configured before transcription.")

        params = {
            "model": "nova-2-phonecall",
            "diarize": "true",
            "detect_language": "true",
        }
        headers = {"Authorization": f"Token {self.api_key}"}
        payload = {"url": gcs_uri}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                params=params,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        return _format_deepgram_transcript(response.json())


def _format_deepgram_transcript(response_json: dict[str, Any]) -> str:
    """Format Deepgram paragraphs into a speaker-labeled transcript."""

    alternatives = (
        response_json.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])
    )
    alternative = alternatives[0] if alternatives else {}
    paragraphs = alternative.get("paragraphs", {}).get("paragraphs", [])

    lines: list[str] = []
    for paragraph in paragraphs:
        speaker = paragraph.get("speaker")
        label = _speaker_label(speaker)
        text = " ".join(sentence.get("text", "") for sentence in paragraph.get("sentences", []))
        if text:
            lines.append(f"[{label}]: {text}")

    if lines:
        return "\n".join(lines)

    transcript = alternative.get("transcript")
    if isinstance(transcript, str) and transcript:
        return transcript

    raise ValueError("Deepgram response did not include a transcript.")


def _speaker_label(speaker: Any) -> str:
    """Convert Deepgram speaker identifiers into readable labels."""

    if speaker == 0:
        return "Agent"
    if speaker == 1:
        return "Lead"
    if speaker is None:
        return "Unknown"
    return f"Speaker {speaker}"
