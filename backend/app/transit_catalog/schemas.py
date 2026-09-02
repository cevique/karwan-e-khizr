from typing import Optional

from pydantic import BaseModel, ConfigDict


class RouteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agency_id: int
    agency_name: str
    short_name: str
    long_name: Optional[str] = None
    route_type: str
    color: Optional[str] = None
    text_color: Optional[str] = None
    has_geometry: bool = False


class RouteListResponse(BaseModel):
    routes: list[RouteSummary]
    total: int
    limit: int
    offset: int


class StopSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    external_key: Optional[str] = None
    lat: float
    lon: float
    zone_id: Optional[str] = None
    coordinate_confidence: Optional[str] = None


class StopListResponse(BaseModel):
    stops: list[StopSummary]
    total: int
    limit: int
    offset: int
