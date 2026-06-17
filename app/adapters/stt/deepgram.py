"""Deepgram speech-to-text adapter."""

from typing import Any, cast

from deepgram import AsyncDeepgramClient

from app.adapters.stt.base import STTAdapter
from app.storage.gcs import download_bytes


class DeepgramAdapter(STTAdapter):
    """Deepgram Python SDK adapter using the nova-2-phonecall model."""

    supports_diarization = True
    supports_language_detection = True

    def __init__(self, api_key: str) -> None:
        """Initialize the adapter with a Deepgram API key."""

        self.api_key = api_key

    async def transcribe(self, gcs_uri: str) -> str:
        """Download GCS audio bytes and transcribe them with Deepgram."""

        if not self.api_key:
            raise RuntimeError("DEEPGRAM_API_KEY must be configured before transcription.")

        audio_bytes = await download_bytes(gcs_uri)
        client = AsyncDeepgramClient(api_key=self.api_key)
        response = await client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-2-phonecall",
            diarize=True,
            detect_language=True,
            utterances=True,
        )

        return _format_deepgram_transcript(_response_to_dict(response))


def _response_to_dict(response: Any) -> dict[str, Any]:
    """Convert a Deepgram SDK response model into a plain dictionary."""

    if isinstance(response, dict):
        return response
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        return cast(dict[str, Any], model_dump(mode="json"))
    legacy_dict = getattr(response, "dict", None)
    if callable(legacy_dict):
        return cast(dict[str, Any], legacy_dict())
    raise TypeError("Unsupported Deepgram response type.")


def _format_deepgram_transcript(response_json: dict[str, Any]) -> str:
    """Format Deepgram diarization output into speaker-labeled transcript text."""

    utterance_lines = _format_utterances(response_json)
    if utterance_lines:
        return "\n".join(utterance_lines)

    word_lines = _format_words(response_json)
    if word_lines:
        return "\n".join(word_lines)

    transcript = _first_transcript(response_json)
    if transcript:
        return transcript

    raise ValueError("Deepgram response did not include a transcript.")


def _format_utterances(response_json: dict[str, Any]) -> list[str]:
    """Format Deepgram utterances when available."""

    utterances = response_json.get("results", {}).get("utterances")
    if not isinstance(utterances, list):
        return []

    lines: list[str] = []
    for utterance in utterances:
        if not isinstance(utterance, dict):
            continue
        transcript = utterance.get("transcript")
        if not isinstance(transcript, str) or not transcript.strip():
            continue
        lines.append(f"[{_speaker_label(utterance.get('speaker'))}]: {transcript.strip()}")
    return lines


def _format_words(response_json: dict[str, Any]) -> list[str]:
    """Group consecutive diarized words by speaker."""

    words = _first_words(response_json)
    if not words:
        return []

    lines: list[str] = []
    current_speaker: Any | None = None
    current_words: list[str] = []

    for word in words:
        if not isinstance(word, dict):
            continue
        text = _word_text(word)
        if not text:
            continue

        speaker = word.get("speaker")
        if current_words and speaker != current_speaker:
            lines.append(f"[{_speaker_label(current_speaker)}]: {' '.join(current_words)}")
            current_words = []

        current_speaker = speaker
        current_words.append(text)

    if current_words:
        lines.append(f"[{_speaker_label(current_speaker)}]: {' '.join(current_words)}")

    return lines


def _first_words(response_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Return words from the first Deepgram alternative."""

    alternative = _first_alternative(response_json)
    if alternative is None:
        return []
    words = alternative.get("words")
    if not isinstance(words, list):
        return []
    return [word for word in words if isinstance(word, dict)]


def _first_transcript(response_json: dict[str, Any]) -> str | None:
    """Return the first plain transcript when diarized segments are unavailable."""

    alternative = _first_alternative(response_json)
    if alternative is None:
        return None
    transcript = alternative.get("transcript")
    return transcript if isinstance(transcript, str) and transcript else None


def _first_alternative(response_json: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first channel alternative from a Deepgram response."""

    channels = response_json.get("results", {}).get("channels")
    if not isinstance(channels, list) or not channels:
        return None
    first_channel = channels[0]
    if not isinstance(first_channel, dict):
        return None
    alternatives = first_channel.get("alternatives")
    if not isinstance(alternatives, list) or not alternatives:
        return None
    first_alternative = alternatives[0]
    return first_alternative if isinstance(first_alternative, dict) else None


def _word_text(word: dict[str, Any]) -> str | None:
    """Return the most readable Deepgram word token."""

    text = word.get("punctuated_word") or word.get("word")
    if not isinstance(text, str) or not text.strip():
        return None
    return text.strip()


def _speaker_label(speaker: Any) -> str:
    """Convert Deepgram speaker identifiers into app-level speaker labels."""

    if speaker == 0:
        return "Agent"
    if speaker == 1:
        return "Lead"
    if speaker is None:
        return "Unknown"
    return f"Speaker {speaker}"
