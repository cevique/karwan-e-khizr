from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class VehiclePosition(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    route_id: int
    trip_id: int
    latitude: float
    longitude: float
    bearing: Optional[float] = None
    speed: Optional[float] = None
    status: Literal["scheduled", "active", "completed"]
    source: Literal["simulated", "realtime"]
    timestamp: datetime
    next_stop_id: Optional[int] = None
    eta_seconds: Optional[int] = None


class VehiclePositionResponse(BaseModel):
    vehicles: list[VehiclePosition]


class VehicleETA(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle_id: int
    next_stop_id: int
    baseline_eta_seconds: int
    predicted_eta_seconds: Optional[int] = None
    delay_seconds: Optional[int] = None
    source: Literal["simulated", "realtime"]


class VehicleSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle: VehiclePosition
    route_geometry: Optional[dict] = None


class VehicleSnapshotResponse(BaseModel):
    vehicles: list[VehicleSnapshot]


class StopTimeEntry(BaseModel):
    stop_id: int
    sequence: int
    arrival_offset_s: int
    departure_offset_s: int
    lat: float
    lon: float


class ScheduleData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trip_id: int
    route_id: int
    route_short_name: str
    vehicle_label: str
    scheduled_start_time: datetime
    stops: list[StopTimeEntry]