from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class FareQuote(BaseModel):
    base_fare: float
    per_leg_fare: float
    total: float
    currency: str = "PKR"


class JourneySearchRequest(BaseModel):
    origin: str
    destination: str
    objective: Literal["fastest", "fewest_transfers", "least_walking"] = "fastest"
    max_walk_m: Optional[float] = Field(default=None, ge=0, le=2000)
    max_transfers: Optional[int] = Field(default=None, ge=0, le=5)
    departure_time: Optional[datetime] = None


class Leg(BaseModel):
    type: Literal["walk", "ride"]
    route_id: Optional[int] = None
    trip_id: Optional[int] = None
    start_stop_id: int
    end_stop_id: int
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    duration_s: int
    distance_m: Optional[float] = None
    geometry: Optional[dict] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None


class Journey(BaseModel):
    legs: list[Leg]
    total_duration_s: int
    total_walk_m: float
    transfer_count: int
    fare: Optional[FareQuote] = None


class LocationResolved(BaseModel):
    name: str
    lat: float
    lon: float


class JourneySearchResponse(BaseModel):
    journeys: list[Journey]
    origin_resolved: LocationResolved
    destination_resolved: LocationResolved


class AmbiguousLocationResponse(BaseModel):
    error: Literal["ambiguous_origin", "ambiguous_destination"]
    candidates: list[LocationResolved]


class NoRouteFoundResponse(BaseModel):
    error: Literal["no_route_found"]
    message: str