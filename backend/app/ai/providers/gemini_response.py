import json
import httpx
from typing import Optional

from app.ai.schemas import ResponseLLMResult
from app.ai.providers.interfaces import JourneyResponseLLMProvider
from app.core.config import settings
from app.core.exceptions import ProviderError
from app.ai.prompts import RESPONSE_SYSTEM_PROMPT


class GeminiResponseProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or settings.REQUEST2_GEMINI_API_KEY
        self.model = model or settings.REQUEST2_GEMINI_MODEL
        self.base_url = (base_url or settings.REQUEST2_GEMINI_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def generate_response(self, authoritative_json: dict) -> ResponseLLMResult:
        if not self.api_key:
            raise ProviderError(
                message="Request #2 Gemini API key not configured",
                provider="gemini",
            )

        if not authoritative_json:
            raise ProviderError(
                message="Empty authoritative JSON provided for response generation",
                provider="gemini",
            )

        client = await self._get_client()

        prompt = f"{RESPONSE_SYSTEM_PROMPT}\n\nAuthoritative JSON:\n{json.dumps(authoritative_json, ensure_ascii=False)}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 2048,
            },
        }

        try:
            response = await client.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("candidates", [{}])[0].get("content", {})
            parts = content.get("parts", [{}])
            text_response = parts[0].get("text", "").strip()

            return ResponseLLMResult(
                text_response=text_response,
                provider="gemini",
                fallback_used=False,
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ProviderError(
                    message="Gemini rate limit exceeded",
                    provider="gemini",
                    details={"status_code": e.response.status_code},
                )
            else:
                raise ProviderError(
                    message=f"Gemini API error: {e.response.status_code}",
                    provider="gemini",
                    details={"status_code": e.response.status_code},
                )
        except httpx.TimeoutException:
            raise ProviderError(
                message="Gemini request timed out",
                provider="gemini",
            )
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(
                message=f"Gemini response generation failed: {str(e)}",
                provider="gemini",
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


async def get_gemini_response_provider() -> GeminiResponseProvider:
    return GeminiResponseProvider()