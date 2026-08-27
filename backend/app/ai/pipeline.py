from datetime import datetime
from typing import Literal, Optional

from app.ai.schemas import IntentResult, IntentLLMResult, ResponseLLMResult, SpeechToTextResult
from app.ai.speech_to_text import SpeechToTextService, get_speech_to_text_service
from app.ai.intent_llm import IntentLLMService, get_intent_llm_service
from app.ai.response_llm import ResponseLLMService, get_response_llm_service
from app.core.config import settings
from app.core.exceptions import (
    AIProviderError,
    ProviderError,
    ValidationError,
)
from app.routing.engine import JourneySearchEngine, get_journey_search_engine
from app.routing.schemas import (
    JourneySearchResponse,
    AmbiguousLocationResponse,
    NoRouteFoundResponse,
    LocationResolved,
)
from sqlalchemy.ext.asyncio import AsyncSession


WALKING_DISTANCE_CLASS_MAPPING = {
    "strict": 300.0,
    "moderate": 600.0,
    "relaxed": 1000.0,
}


class ConversationPipeline:
    def __init__(
        self,
        speech_to_text_service: SpeechToTextService | None = None,
        intent_llm_service: IntentLLMService | None = None,
        response_llm_service: ResponseLLMService | None = None,
    ):
        self._speech_to_text = speech_to_text_service
        self._intent_llm = intent_llm_service
        self._response_llm = response_llm_service
        self._journey_engine: JourneySearchEngine | None = None

    async def _get_speech_to_text(self) -> SpeechToTextService:
        if self._speech_to_text is None:
            self._speech_to_text = await get_speech_to_text_service()
        return self._speech_to_text

    async def _get_intent_llm(self) -> IntentLLMService:
        if self._intent_llm is None:
            self._intent_llm = await get_intent_llm_service()
        return self._intent_llm

    async def _get_response_llm(self) -> ResponseLLMService:
        if self._response_llm is None:
            self._response_llm = await get_response_llm_service()
        return self._response_llm

    def _get_journey_engine(self, session: AsyncSession) -> JourneySearchEngine:
        if self._journey_engine is None:
            self._journey_engine = get_journey_search_engine(session)
        return self._journey_engine

    def _map_walking_distance_class(
        self, walking_class: Optional[str | float]
    ) -> Optional[float]:
        if walking_class is None:
            return None
        if isinstance(walking_class, (int, float)):
            return float(walking_class)
        return WALKING_DISTANCE_CLASS_MAPPING.get(walking_class)

    async def process_text(
        self,
        text: str,
        session: AsyncSession,
    ) -> dict:
        intent_service = await self._get_intent_llm()

        try:
            intent_result: IntentLLMResult = await intent_service.extract_intent(text)
        except ProviderError as e:
            raise AIProviderError(
                message=f"Intent extraction failed: {e.message}",
                request_stage=1,
                provider=e.details.get("provider", "unknown"),
                details=e.details,
            )

        intent = intent_result.intent

        if intent.ambiguous_fields:
            clarification_error = self._build_clarification_response(
                intent.ambiguous_fields,
                "origin" if "origin" in intent.ambiguous_fields else "destination",
            )
            response_service = await self._get_response_llm()
            try:
                response_result = await response_service.generate_response(
                    clarification_error
                )
                text_response = response_result.text_response
            except ProviderError as e:
                text_response = self._fallback_clarification_message(
                    intent.ambiguous_fields
                )

            return {
                "structured_journeys": None,
                "text_response": text_response,
                "clarification_needed": {
                    "field": "origin"
                    if "origin" in intent.ambiguous_fields
                    else "destination",
                    "candidates": [],
                },
            }

        max_walk_m = self._map_walking_distance_class(
            intent.max_walking_distance_class
        )

        try:
            departure_time = None
            if intent.departure_time:
                departure_time = datetime.fromisoformat(
                    intent.departure_time.replace("Z", "+00:00")
                )
        except ValueError:
            raise ValidationError(
                "Invalid departure_time format. Use ISO 8601.",
                details={"field": "departure_time"},
            )

        journey_engine = self._get_journey_engine(session)
        search_result = await journey_engine.search(
            origin=intent.origin,
            destination=intent.destination,
            objective=intent.objective,
            max_walk_m=max_walk_m,
            max_transfers=intent.max_transfers,
            departure_time=departure_time,
        )

        response_service = await self._get_response_llm()

        if isinstance(search_result, AmbiguousLocationResponse):
            clarification_json = {
                "error": search_result.error,
                "candidates": [
                    {"name": c.name, "lat": c.lat, "lon": c.lon}
                    for c in search_result.candidates
                ],
            }
            try:
                response_result = await response_service.generate_response(
                    clarification_json
                )
                text_response = response_result.text_response
            except ProviderError as e:
                text_response = self._fallback_clarification_message(
                    [search_result.error.replace("ambiguous_", "")]
                )

            return {
                "structured_journeys": None,
                "text_response": text_response,
                "clarification_needed": {
                    "field": search_result.error.replace("ambiguous_", ""),
                    "candidates": [
                        {"name": c.name, "lat": c.lat, "lon": c.lon}
                        for c in search_result.candidates
                    ],
                },
            }

        if isinstance(search_result, NoRouteFoundResponse):
            no_route_json = {
                "error": "no_route_found",
                "message": search_result.message,
            }
            try:
                response_result = await response_service.generate_response(
                    no_route_json
                )
                text_response = response_result.text_response
            except ProviderError as e:
                text_response = "I couldn't find a transit route between those locations. Please check the names and try again."

            return {
                "structured_journeys": None,
                "text_response": text_response,
                "clarification_needed": None,
            }

        authoritative_json = search_result.model_dump()

        try:
            response_result: ResponseLLMResult = await response_service.generate_response(
                authoritative_json
            )
            text_response = response_result.text_response
            response_error = None
        except ProviderError as e:
            text_response = None
            response_error = "response_generation_failed"

        return {
            "structured_journeys": authoritative_json,
            "text_response": text_response,
            "text_response_error": response_error,
            "clarification_needed": None,
        }

    async def process_audio(
        self,
        audio_bytes: bytes,
        content_type: str,
        session: AsyncSession,
    ) -> dict:
        stt_service = await self._get_speech_to_text()

        try:
            stt_result: SpeechToTextResult = await stt_service.transcribe(
                audio_bytes, content_type
            )
        except ProviderError as e:
            raise AIProviderError(
                message=f"Speech-to-text failed: {e.message}",
                request_stage=0,
                provider=e.details.get("provider", "groq_whisper"),
                details=e.details,
            )

        transcript_text = stt_result.transcript.text
        if not transcript_text:
            raise ValidationError(
                "Transcription produced empty text",
                details={"transcript_confidence": stt_result.transcript.confidence},
            )

        return await self.process_text(transcript_text, session)

    def _build_clarification_response(
        self, ambiguous_fields: list[str], primary_field: str
    ) -> dict:
        field_names = {
            "origin": "starting location",
            "destination": "destination",
        }
        field_display = field_names.get(primary_field, primary_field)
        candidates = []
        return {
            "error": f"ambiguous_{primary_field}",
            "candidates": candidates,
        }

    def _fallback_clarification_message(
        self, ambiguous_fields: list[str]
    ) -> str:
        if "origin" in ambiguous_fields and "destination" in ambiguous_fields:
            return "I need both a starting point and a destination to find a route. Please specify both."
        elif "origin" in ambiguous_fields:
            return "I couldn't determine your starting location. Please specify where you're starting from."
        elif "destination" in ambiguous_fields:
            return "I couldn't determine your destination. Please specify where you want to go."
        return "I need more information to find a route. Please clarify your request."

    async def close(self) -> None:
        if self._speech_to_text:
            await self._speech_to_text.close()
        if self._intent_llm:
            await self._intent_llm.close()
        if self._response_llm:
            await self._response_llm.close()


_conversation_pipeline: ConversationPipeline | None = None


async def get_conversation_pipeline() -> ConversationPipeline:
    global _conversation_pipeline
    if _conversation_pipeline is None:
        _conversation_pipeline = ConversationPipeline()
    return _conversation_pipeline