"""Google Speech-to-Text fallback adapter."""

from app.adapters.stt.base import STTAdapter


class GoogleSTTAdapter(STTAdapter):
    """Fallback adapter for Google Speech-to-Text."""

    supports_diarization = False
    supports_language_detection = False

    async def transcribe(self, gcs_uri: str) -> str:
        """Fallback adapter; implement if Deepgram quality is insufficient."""

        _ = gcs_uri
        raise NotImplementedError(
            "Google STT fallback is pending quality evaluation against Deepgram output."
        )
