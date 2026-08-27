from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.service import AdminService
from app.admin.schemas import (
    DataStatusResponse,
    SimulationStatusResponse,
    AdminTicketListResponse,
    AdminTicketResponse,
    SeedRunResponse,
    SimulationStartResponse,
    SimulationStopResponse,
)
from app.core.database import get_db
from app.users.dependencies import AdminUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/data/status", response_model=DataStatusResponse)
async def get_data_status(
    admin: AdminUser,
    session: AsyncSession = Depends(get_db),
) -> DataStatusResponse:
    service = AdminService(session)
    return await service.get_data_status()


@router.get("/simulation/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    admin: AdminUser,
    session: AsyncSession = Depends(get_db),
) -> SimulationStatusResponse:
    service = AdminService(session)
    return await service.get_simulation_status()


@router.get("/tickets", response_model=AdminTicketListResponse)
async def search_tickets(
    admin: AdminUser,
    session: AsyncSession = Depends(get_db),
    status: str | None = Query(default=None, description="Filter by ticket status"),
    code: str | None = Query(default=None, description="Filter by QR code"),
) -> AdminTicketListResponse:
    service = AdminService(session)
    return await service.search_tickets(status=status, code=code)


@router.get("/tickets/{ticket_id}", response_model=AdminTicketResponse)
async def get_ticket(
    ticket_id: int,
    admin: AdminUser,
    session: AsyncSession = Depends(get_db),
) -> AdminTicketResponse:
    service = AdminService(session)
    return await service.get_ticket_details(ticket_id)


@router.post("/seed/run", response_model=SeedRunResponse)
async def run_seed(
    admin: AdminUser,
    session: AsyncSession = Depends(get_db),
) -> SeedRunResponse:
    service = AdminService(session)
    return await service.run_seed()


@router.post("/simulation/start", response_model=SimulationStartResponse)
async def start_simulation(
    admin: AdminUser,
    session: AsyncSession = Depends(get_db),
) -> SimulationStartResponse:
    service = AdminService(session)
    return await service.start_simulation()


@router.post("/simulation/stop", response_model=SimulationStopResponse)
async def stop_simulation(
    admin: AdminUser,
    session: AsyncSession = Depends(get_db),
) -> SimulationStopResponse:
    service = AdminService(session)
    return await service.stop_simulation()
