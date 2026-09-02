from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.transit_catalog.schemas import (
    RouteListResponse,
    RouteSummary,
    StopListResponse,
    StopSummary,
)
from app.transit_catalog.service import TransitCatalogService

router = APIRouter(prefix="/transit", tags=["transit-catalog"])


@router.get("/routes", response_model=RouteListResponse)
async def list_routes(
    session: AsyncSession = Depends(get_db),
    route_type: Literal["bus", "metro", "feeder"] | None = Query(
        default=None, description="Filter by route type"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> RouteListResponse:
    service = TransitCatalogService(session)
    return await service.list_routes(route_type=route_type, limit=limit, offset=offset)


@router.get("/routes/{route_id}", response_model=RouteSummary)
async def get_route(
    route_id: int,
    session: AsyncSession = Depends(get_db),
) -> RouteSummary:
    service = TransitCatalogService(session)
    return await service.get_route(route_id)


@router.get("/stops", response_model=StopListResponse)
async def list_stops(
    session: AsyncSession = Depends(get_db),
    search: str | None = Query(default=None, description="Filter stops by name (case-insensitive substring)"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> StopListResponse:
    service = TransitCatalogService(session)
    return await service.list_stops(search=search, limit=limit, offset=offset)


@router.get("/stops/{stop_id}", response_model=StopSummary)
async def get_stop(
    stop_id: int,
    session: AsyncSession = Depends(get_db),
) -> StopSummary:
    service = TransitCatalogService(session)
    return await service.get_stop(stop_id)
