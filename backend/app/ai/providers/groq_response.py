import json
import httpx
from typing import Optional

from app.ai.schemas import ResponseLLMResult
from app.ai.providers.interfaces import JourneyResponseLLMProvider
from app.core.config import settings
from app.core.exceptions import ProviderError
from app.ai.prompts import RESPONSE_SYSTEM_PROMPT


class GroqResponseProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or settings.REQUEST2_GROQ_API_KEY
        self.model = model or settings.REQUEST2_GROQ_MODEL
        self.base_url = (base_url or settings.REQUEST2_GROQ_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        return self._client

    async def generate_response(self, authoritative_json: dict) -> ResponseLLMResult:
        if not self.api_key:
            raise ProviderError(
                message="Request #2 Groq API key not configured",
                provider="groq",
            )

        if not authoritative_json:
            raise ProviderError(
                message="Empty authoritative JSON provided for response generation",
                provider="groq",
            )

        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Authoritative JSON:\n{json.dumps(authoritative_json, ensure_ascii=False)}"},
            ],
            "temperature": 0.3,
            "top_p": 0.8,
            "max_tokens": 2048,
        }

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            text_response = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            return ResponseLLMResult(
                text_response=text_response,
                provider="groq",
                fallback_used=False,
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
                message=f"Groq response generation failed: {str(e)}",
                provider="groq",
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


async def get_groq_response_provider() -> GroqResponseProvider:
    return GroqResponseProvider()