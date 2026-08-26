from pydantic import BaseModel, Field
from typing import Literal, Optional


class LocationCandidate(BaseModel):
    stop_id: Optional[int] = None
    name: str
    lat: float
    lon: float
    match_confidence: float = Field(ge=0.0, le=1.0)
    match_type: Literal["exact_stop", "fuzzy_stop", "geocoded"]


class LocationResolutionResult(BaseModel):
    candidates: list[LocationCandidate]


class NearbyStop(BaseModel):
    stop_id: int
    name: str
    lat: float
    lon: float
    distance_m: float


class WalkingResult(BaseModel):
    distance_m: float
    duration_s: float
    source: Literal["osrm", "haversine"] = "haversine"


class RouteGeometryResult(BaseModel):
    route_id: int
    geometry: Optional[dict] = None
    geometry_source: Optional[str] = None
    geometry_confidence: Optional[str] = None


ISLAMABAD_BOUNDS = {
    "min_lat": 33.0,
    "max_lat": 34.5,
    "min_lon": 72.5,
    "max_lon": 73.5,
}