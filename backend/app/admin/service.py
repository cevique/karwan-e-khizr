from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    DataStatusResponse,
    StopsStatus,
    RoutesStatus,
    AgenciesStatus,
    SimulationStatusResponse,
    AdminTicketResponse,
    AdminTicketListResponse,
    SeedRunResponse,
    SimulationStartResponse,
    SimulationStopResponse,
)
from app.db.models.agency import Agency
from app.db.models.route import Route
from app.db.models.stop import Stop
from app.db.models.stop_time import StopTime
from app.db.models.ticket import Ticket
from app.db.models.trip import Trip
from app.db.models.vehicle import Vehicle


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_data_status(self) -> DataStatusResponse:
        stops_total = await self._count(Stop)
        stops_with_coords = await self._count(
            Stop, Stop.location.isnot(None)
        )

        routes_total = await self._count(Route)
        routes_with_geometry = await self._count(
            Route, Route.path.isnot(None)
        )

        routes_with_timetable = await self._count_distinct(
            Trip, Trip.route_id
        )

        agencies_total = await self._count(Agency)

        return DataStatusResponse(
            stops=StopsStatus(
                total=stops_total,
                with_coordinates=stops_with_coords,
                without_coordinates=stops_total - stops_with_coords,
            ),
            routes=RoutesStatus(
                total=routes_total,
                with_geometry=routes_with_geometry,
                without_geometry=routes_total - routes_with_geometry,
                with_timetable=routes_with_timetable,
                without_timetable=routes_total - routes_with_timetable,
            ),
            agencies=AgenciesStatus(total=agencies_total),
        )

    async def get_simulation_status(self) -> SimulationStatusResponse:
        active_vehicles = await self._count(
            Vehicle, Vehicle.status == "active"
        )
        active_trips = await self._count(
            Trip, Trip.status == "active"
        )

        running = active_vehicles > 0 or active_trips > 0

        return SimulationStatusResponse(
            running=running,
            active_vehicles=active_vehicles,
            active_trips=active_trips,
            simulation_time=datetime.now(timezone.utc) if running else None,
        )

    async def search_tickets(
        self,
        status: str | None = None,
        code: str | None = None,
    ) -> AdminTicketListResponse:
        query = select(Ticket)

        if status is not None:
            query = query.where(Ticket.status == status)

        if code is not None:
            query = query.where(Ticket.qr_payload == code)

        query = query.order_by(Ticket.created_at.desc()).limit(100)

        result = await self.session.execute(query)
        tickets = result.scalars().all()

        return AdminTicketListResponse(
            tickets=[
                AdminTicketResponse(
                    id=t.id,
                    user_id=t.user_id,
                    status=t.status,
                    fare_charged=t.fare_charged,
                    created_at=t.created_at,
                )
                for t in tickets
            ]
        )

    async def get_ticket_details(self, ticket_id: int) -> AdminTicketResponse:
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()

        if ticket is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"Ticket {ticket_id} not found")

        return AdminTicketResponse(
            id=ticket.id,
            user_id=ticket.user_id,
            status=ticket.status,
            fare_charged=ticket.fare_charged,
            created_at=ticket.created_at,
        )

    async def run_seed(self) -> SeedRunResponse:
        from app.seeding.importer import TransitDataImporter, load_transit_data

        data_path = Path(__file__).parent.parent.parent / "data" / "transit_data.json"
        if not data_path.exists():
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"Transit data file not found at {data_path}")

        data = load_transit_data(data_path)
        importer = TransitDataImporter(self.session)
        results = await importer.import_all(data)
        await self.session.commit()

        return SeedRunResponse(
            status="completed",
            imported=results,
        )

    async def start_simulation(self) -> SimulationStartResponse:
        from app.simulation.trip_generator import TripGenerator
        from app.simulation.engine import SimulationEngine

        engine = SimulationEngine()
        generator = TripGenerator(self.session, engine)
        vehicles = await generator.ensure_vehicles_exist()
        await self.session.commit()

        return SimulationStartResponse(
            status="started",
            message=f"Simulation started with {len(vehicles)} vehicles",
        )

    async def stop_simulation(self) -> SimulationStopResponse:
        result = await self.session.execute(
            select(Vehicle).where(Vehicle.status == "active")
        )
        vehicles = result.scalars().all()

        count = len(vehicles)
        for vehicle in vehicles:
            vehicle.status = "completed"

        trip_result = await self.session.execute(
            select(Trip).where(Trip.status == "active")
        )
        trips = trip_result.scalars().all()

        for trip in trips:
            trip.status = "completed"

        await self.session.commit()

        return SimulationStopResponse(
            status="stopped",
            message=f"Simulation stopped, {count} vehicles deactivated",
        )

    async def _count(self, model: Any, *filters: Any) -> int:
        query = select(func.count()).select_from(model)
        for f in filters:
            query = query.where(f)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_distinct(self, model: Any, column: Any) -> int:
        query = select(func.count(func.distinct(column))).select_from(model)
        result = await self.session.execute(query)
        return result.scalar() or 0
