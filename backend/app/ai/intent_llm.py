from typing import Optional

from app.ai.schemas import IntentResult, IntentLLMResult
from app.ai.providers.interfaces import IntentLLMProvider
from app.ai.providers.gemini_intent import GeminiIntentProvider
from app.ai.providers.groq_intent import GroqIntentProvider
from app.core.exceptions import ProviderError
from app.core.config import settings


class IntentLLMService:
    def __init__(
        self,
        primary_provider: IntentLLMProvider | None = None,
        fallback_provider: IntentLLMProvider | None = None,
    ):
        self._primary = primary_provider
        self._fallback = fallback_provider

    async def _get_primary(self) -> IntentLLMProvider:
        if self._primary is None:
            if settings.REQUEST1_GEMINI_API_KEY:
                self._primary = GeminiIntentProvider()
            elif settings.REQUEST1_GROQ_API_KEY:
                self._primary = GroqIntentProvider()
            else:
                raise ProviderError(
                    message="No Request #1 provider configured (need REQUEST1_GEMINI_API_KEY or REQUEST1_GROQ_API_KEY)",
                    provider="intent_llm",
                )
        return self._primary

    async def _get_fallback(self) -> IntentLLMProvider | None:
        if self._fallback is None:
            primary = await self._get_primary()
            primary_name = getattr(primary, "model", "unknown") if hasattr(primary, "model") else "gemini"
            
            # Determine fallback based on what primary is
            if isinstance(primary, GeminiIntentProvider) and settings.REQUEST1_GROQ_API_KEY:
                self._fallback = GroqIntentProvider()
            elif isinstance(primary, GroqIntentProvider) and settings.REQUEST1_GEMINI_API_KEY:
                self._fallback = GeminiIntentProvider()
        return self._fallback

    async def extract_intent(self, text: str) -> IntentLLMResult:
        primary = await self._get_primary()

        try:
            result = await primary.extract_intent(text)
            return result
        except ProviderError as primary_error:
            fallback = await self._get_fallback()
            primary_provider = primary_error.details.get("provider", "unknown") if primary_error.details else "unknown"
            if fallback is None:
                raise ProviderError(
                    message=f"Request #1 failed (primary: {primary_provider}): {primary_error.message}. No fallback available.",
                    provider="intent_llm",
                    details={"primary_error": str(primary_error), "fallback_available": False},
                )

            try:
                result = await fallback.extract_intent(text)
                result.fallback_used = True
                return result
            except ProviderError as fallback_error:
                fallback_provider = fallback_error.details.get("provider", "unknown") if fallback_error.details else "unknown"
                raise ProviderError(
                    message=f"Request #1 failed (primary: {primary_provider}, fallback: {fallback_provider}): {primary_error.message} | {fallback_error.message}",
                    provider="intent_llm",
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


_intent_llm_service: IntentLLMService | None = None


async def get_intent_llm_service() -> IntentLLMService:
    global _intent_llm_service
    if _intent_llm_service is None:
        _intent_llm_service = IntentLLMService()
    return _intent_llm_service