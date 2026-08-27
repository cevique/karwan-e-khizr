from typing import Optional

from app.ai.schemas import ResponseLLMResult
from app.ai.providers.interfaces import JourneyResponseLLMProvider
from app.ai.providers.gemini_response import GeminiResponseProvider
from app.ai.providers.groq_response import GroqResponseProvider
from app.core.exceptions import ProviderError
from app.core.config import settings


class ResponseLLMService:
    def __init__(
        self,
        primary_provider: JourneyResponseLLMProvider | None = None,
        fallback_provider: JourneyResponseLLMProvider | None = None,
    ):
        self._primary = primary_provider
        self._fallback = fallback_provider

    async def _get_primary(self) -> JourneyResponseLLMProvider:
        if self._primary is None:
            if settings.REQUEST2_GEMINI_API_KEY:
                self._primary = GeminiResponseProvider()
            elif settings.REQUEST2_GROQ_API_KEY:
                self._primary = GroqResponseProvider()
            else:
                raise ProviderError(
                    message="No Request #2 provider configured (need REQUEST2_GEMINI_API_KEY or REQUEST2_GROQ_API_KEY)",
                    provider="response_llm",
                )
        return self._primary

    async def _get_fallback(self) -> JourneyResponseLLMProvider | None:
        if self._fallback is None:
            primary = await self._get_primary()
            
            if isinstance(primary, GeminiResponseProvider) and settings.REQUEST2_GROQ_API_KEY:
                self._fallback = GroqResponseProvider()
            elif isinstance(primary, GroqResponseProvider) and settings.REQUEST2_GEMINI_API_KEY:
                self._fallback = GeminiResponseProvider()
        return self._fallback

    async def generate_response(self, authoritative_json: dict) -> ResponseLLMResult:
        primary = await self._get_primary()

        try:
            result = await primary.generate_response(authoritative_json)
            return result
        except ProviderError as primary_error:
            fallback = await self._get_fallback()
            primary_provider = primary_error.details.get("provider", "unknown") if primary_error.details else "unknown"
            if fallback is None:
                raise ProviderError(
                    message=f"Request #2 failed (primary: {primary_provider}): {primary_error.message}. No fallback available.",
                    provider="response_llm",
                    details={"primary_error": str(primary_error), "fallback_available": False},
                )

            try:
                result = await fallback.generate_response(authoritative_json)
                result.fallback_used = True
                return result
            except ProviderError as fallback_error:
                fallback_provider = fallback_error.details.get("provider", "unknown") if fallback_error.details else "unknown"
                raise ProviderError(
                    message=f"Request #2 failed (primary: {primary_provider}, fallback: {fallback_provider}): {primary_error.message} | {fallback_error.message}",
                    provider="response_llm",
                    details={
                        "primary_error": str(primary_error),
                        "fallback_error": str(fallback_error),
                    },
                )

    async def close(self) -> None:
        if self._primary and hasattr(self._primary, "close"):
            await self._primary.close()
        if self._fallback and hasattr(self._fallback, "close"):
            await self._fallback.close()


_response_llm_service: ResponseLLMService | None = None


async def get_response_llm_service() -> ResponseLLMService:
    global _response_llm_service
    if _response_llm_service is None:
        _response_llm_service = ResponseLLMService()
    return _response_llm_service