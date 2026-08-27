from abc import ABC, abstractmethod
from typing import Protocol

from app.ai.schemas import Transcript, IntentResult, IntentLLMResult, ResponseLLMResult


class SpeechToTextProvider(Protocol):
    async def transcribe(self, audio_bytes: bytes, content_type: str = "audio/wav") -> Transcript: ...


class IntentLLMProvider(Protocol):
    async def extract_intent(self, text: str) -> IntentLLMResult: ...


class JourneyResponseLLMProvider(Protocol):
    async def generate_response(self, authoritative_json: dict) -> ResponseLLMResult: ...