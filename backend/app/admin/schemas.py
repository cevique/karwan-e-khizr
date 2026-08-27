from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class StopsStatus(BaseModel):
    total: int
    with_coordinates: int
    without_coordinates: int


class RoutesStatus(BaseModel):
    total: int
    with_geometry: int
    without_geometry: int
    with_timetable: int
    without_timetable: int


class AgenciesStatus(BaseModel):
    total: int


class DataStatusResponse(BaseModel):
    stops: StopsStatus
    routes: RoutesStatus
    agencies: AgenciesStatus


class SimulationStatusResponse(BaseModel):
    running: bool
    active_vehicles: int
    active_trips: int
    simulation_time: datetime | None = None


class AdminTicketResponse(BaseModel):
    id: int
    user_id: int
    status: Literal["ACTIVE", "USED", "EXPIRED", "REVOKED"]
    fare_charged: float
    created_at: datetime


class AdminTicketListResponse(BaseModel):
    tickets: list[AdminTicketResponse]


class SeedRunResponse(BaseModel):
    status: str
    imported: dict[str, int]


class SimulationStartResponse(BaseModel):
    status: str
    message: str


class SimulationStopResponse(BaseModel):
    status: str
    message: str
