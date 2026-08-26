from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.simulation.engine import SimulationEngine
from app.simulation.provider import SimulatedVehicleLocationProvider
from app.simulation.schemas import (
    VehiclePositionResponse,
    VehicleETA,
)

router = APIRouter(prefix="/transit/realtime")

_simulation_engine = SimulationEngine()


def get_simulation_engine() -> SimulationEngine:
    return _simulation_engine


def get_vehicle_provider(db: AsyncSession = Depends(get_db)) -> SimulatedVehicleLocationProvider:
    return SimulatedVehicleLocationProvider(engine=_simulation_engine, db=db)


@router.get("/vehicles", response_model=VehiclePositionResponse)
async def list_vehicles(
    provider: SimulatedVehicleLocationProvider = Depends(get_vehicle_provider),
):
    positions = await provider.get_all_positions()
    return VehiclePositionResponse(vehicles=positions)


@router.get("/vehicles/{vehicle_id}")
async def get_vehicle(
    vehicle_id: int,
    provider: SimulatedVehicleLocationProvider = Depends(get_vehicle_provider),
):
    position = await provider.get_vehicle_position(vehicle_id)
    if position is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    return position


@router.get("/vehicles/{vehicle_id}/eta", response_model=VehicleETA)
async def get_vehicle_eta(
    vehicle_id: int,
    provider: SimulatedVehicleLocationProvider = Depends(get_vehicle_provider),
):
    eta = await provider.get_vehicle_eta(vehicle_id)
    if eta is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found or trip completed")
    return VehicleETA(**eta)