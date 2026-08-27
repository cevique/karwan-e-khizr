from typing import Optional

from app.ai.schemas import Transcript, SpeechToTextResult
from app.ai.providers.interfaces import SpeechToTextProvider
from app.ai.providers.groq_whisper import GroqWhisperProvider
from app.core.exceptions import ProviderError


class SpeechToTextService:
    def __init__(self, provider: SpeechToTextProvider | None = None):
        self._provider = provider

    async def _get_provider(self) -> SpeechToTextProvider:
        if self._provider is None:
            self._provider = GroqWhisperProvider()
        return self._provider

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
    ) -> SpeechToTextResult:
        provider = await self._get_provider()

        try:
            transcript = await provider.transcribe(audio_bytes, content_type)
            return SpeechToTextResult(transcript=transcript, provider="groq_whisper")
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                message=f"Speech-to-text failed: {str(e)}",
                provider="groq_whisper",
            )

    async def close(self) -> None:
        if self._provider and hasattr(self._provider, "close"):
            await self._provider.close()


_speech_to_text_service: SpeechToTextService | None = None


async def get_speech_to_text_service() -> SpeechToTextService:
    global _speech_to_text_service
    if _speech_to_text_service is None:
        _speech_to_text_service = SpeechToTextService()
    return _speech_to_text_service