import json
import httpx
from typing import Optional

from app.ai.schemas import IntentResult, IntentLLMResult
from app.ai.providers.interfaces import IntentLLMProvider
from app.core.config import settings
from app.core.exceptions import ProviderError
from app.ai.prompts import INTENT_SYSTEM_PROMPT


class GeminiIntentProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or settings.REQUEST1_GEMINI_API_KEY
        self.model = model or settings.REQUEST1_GEMINI_MODEL
        self.base_url = (base_url or settings.REQUEST1_GEMINI_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def extract_intent(self, text: str) -> IntentLLMResult:
        if not self.api_key:
            raise ProviderError(
                message="Request #1 Gemini API key not configured",
                provider="gemini",
            )

        if not text or not text.strip():
            raise ProviderError(
                message="Empty text provided for intent extraction",
                provider="gemini",
            )

        client = await self._get_client()

        prompt = f"{INTENT_SYSTEM_PROMPT}\n\nUser text: {text.strip()}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "topP": 0.1,
                "topK": 1,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
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
            raw_text = parts[0].get("text", "").strip()

            parsed = json.loads(raw_text)
            intent = IntentResult(**parsed)

            return IntentLLMResult(
                intent=intent,
                provider="gemini",
                fallback_used=False,
            )

        except json.JSONDecodeError as e:
            raise ProviderError(
                message=f"Gemini returned invalid JSON: {str(e)}",
                provider="gemini",
                details={"raw_response": raw_text if "raw_text" in locals() else "N/A"},
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
                message=f"Gemini intent extraction failed: {str(e)}",
                provider="gemini",
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


async def get_gemini_intent_provider() -> GeminiIntentProvider:
    return GeminiIntentProvider()