from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class FareQuoteRequest(BaseModel):
    ride_leg_count: int = Field(ge=0, le=10)


class FareQuote(BaseModel):
    base_fare: float
    per_leg_fare: float
    total: float
    currency: str = "PKR"


class TicketPurchaseRequest(BaseModel):
    journey_data: dict
    ride_leg_count: int = Field(ge=1, le=10)


class TicketResponse(BaseModel):
    id: int
    status: Literal["ACTIVE", "USED", "EXPIRED", "REVOKED"]
    fare_charged: float
    currency: str
    qr_payload: str
    created_at: datetime
    expires_at: datetime | None = None
    used_at: datetime | None = None
    ride_leg_count: int
    journey_data: dict


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]


class ValidationRequest(BaseModel):
    qr_payload: str


class ValidationResult(BaseModel):
    valid: bool
    ticket_id: int | None = None
    status: Literal["ACTIVE", "USED", "EXPIRED", "REVOKED"] | None = None
    reason: str | None = None


class RevokeRequest(BaseModel):
    pass  # No body needed, ticket ID is in path