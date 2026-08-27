from typing import Literal, Optional
from pydantic import BaseModel, Field


class Transcript(BaseModel):
    text: str
    confidence: Optional[float] = None


class IntentResult(BaseModel):
    """Request #1 output — validated structured intent."""
    origin: str
    destination: str
    objective: Literal["fastest", "fewest_transfers", "least_walking"] = "fastest"
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    max_transfers: Optional[int] = Field(default=None, ge=0, le=5)
    max_walking_distance_class: Optional[Literal["strict", "moderate", "relaxed"] | float] = None
    accessibility: Optional[str] = None
    ambiguous_fields: list[str] = Field(default_factory=list)


class SpeechToTextResult(BaseModel):
    transcript: Transcript
    provider: str = "groq_whisper"


class IntentLLMResult(BaseModel):
    intent: IntentResult
    provider: str
    fallback_used: bool = False


class ResponseLLMResult(BaseModel):
    text_response: str
    provider: str
    fallback_used: bool = False