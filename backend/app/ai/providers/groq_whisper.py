import httpx
from typing import Optional

from app.ai.schemas import Transcript
from app.ai.providers.interfaces import SpeechToTextProvider
from app.core.config import settings
from app.core.exceptions import ProviderError


class GroqWhisperProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or settings.GROQ_WHISPER_API_KEY
        self.model = model or settings.GROQ_WHISPER_MODEL
        self.base_url = (base_url or settings.GROQ_WHISPER_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        return self._client

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
    ) -> Transcript:
        if not self.api_key:
            raise ProviderError(
                message="Groq Whisper API key not configured",
                provider="groq_whisper",
            )

        if not audio_bytes:
            raise ProviderError(
                message="Empty audio data provided",
                provider="groq_whisper",
            )

        client = await self._get_client()

        files = {
            "file": ("audio.wav", audio_bytes, content_type),
            "model": (None, self.model),
            "response_format": (None, "verbose_json"),
        }

        try:
            response = await client.post(
                f"{self.base_url}/audio/transcriptions",
                files=files,
            )
            response.raise_for_status()
            data = response.json()

            text = data.get("text", "").strip()
            confidence = None
            if "segments" in data and data["segments"]:
                avg_confidence = sum(
                    seg.get("avg_logprob", 0) for seg in data["segments"]
                ) / len(data["segments"])
                confidence = max(0.0, min(1.0, (avg_confidence + 1.0)))

            return Transcript(text=text, confidence=confidence)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ProviderError(
                    message="Groq Whisper rate limit exceeded",
                    provider="groq_whisper",
                    details={"status_code": e.response.status_code},
                )
            elif e.response.status_code == 413:
                raise ProviderError(
                    message="Audio file too large",
                    provider="groq_whisper",
                    details={"status_code": e.response.status_code},
                )
            else:
                raise ProviderError(
                    message=f"Groq Whisper API error: {e.response.status_code}",
                    provider="groq_whisper",
                    details={"status_code": e.response.status_code},
                )
        except httpx.TimeoutException:
            raise ProviderError(
                message="Groq Whisper request timed out",
                provider="groq_whisper",
            )
        except Exception as e:
            raise ProviderError(
                message=f"Groq Whisper transcription failed: {str(e)}",
                provider="groq_whisper",
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


async def get_groq_whisper_provider() -> GroqWhisperProvider:
    return GroqWhisperProvider()