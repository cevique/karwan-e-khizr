import json
import httpx
from typing import Optional

from app.ai.schemas import IntentResult, IntentLLMResult
from app.ai.providers.interfaces import IntentLLMProvider
from app.core.config import settings
from app.core.exceptions import ProviderError
from app.ai.prompts import INTENT_SYSTEM_PROMPT


class GroqIntentProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or settings.REQUEST1_GROQ_API_KEY
        self.model = model or settings.REQUEST1_GROQ_MODEL
        self.base_url = (base_url or settings.REQUEST1_GROQ_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        return self._client

    async def extract_intent(self, text: str) -> IntentLLMResult:
        if not self.api_key:
            raise ProviderError(
                message="Request #1 Groq API key not configured",
                provider="groq",
            )

        if not text or not text.strip():
            raise ProviderError(
                message="Empty text provided for intent extraction",
                provider="groq",
            )

        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text.strip()},
            ],
            "temperature": 0.0,
            "top_p": 0.1,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            parsed = json.loads(raw_text)
            intent = IntentResult(**parsed)

            return IntentLLMResult(
                intent=intent,
                provider="groq",
                fallback_used=False,
            )

        except json.JSONDecodeError as e:
            raise ProviderError(
                message=f"Groq returned invalid JSON: {str(e)}",
                provider="groq",
                details={"raw_response": raw_text if "raw_text" in locals() else "N/A"},
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ProviderError(
                    message="Groq rate limit exceeded",
                    provider="groq",
                    details={"status_code": e.response.status_code},
                )
            else:
                raise ProviderError(
                    message=f"Groq API error: {e.response.status_code}",
                    provider="groq",
                    details={"status_code": e.response.status_code},
                )
        except httpx.TimeoutException:
            raise ProviderError(
                message="Groq request timed out",
                provider="groq",
            )
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(
                message=f"Groq intent extraction failed: {str(e)}",
                provider="groq",
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


async def get_groq_intent_provider() -> GroqIntentProvider:
    return GroqIntentProvider()