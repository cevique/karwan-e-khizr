from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.route import Route
from app.db.models.route_stop import RouteStop
from app.db.models.stop import Stop
from app.db.models.stop_time import StopTime
from app.db.models.trip import Trip
from app.db.models.vehicle import Vehicle
from app.simulation.engine import SimulationEngine
from app.simulation.schemas import ScheduleData, StopTimeEntry


class TripGenerator:
    """Generates active trip and vehicle records from schedule data + current time."""

    SERVICE_WINDOW_BEFORE_S: int = 300
    SERVICE_WINDOW_AFTER_S: int = 60

    def __init__(self, db: AsyncSession, engine: SimulationEngine):
        self._db = db
        self._engine = engine

    async def get_current_schedule(self, now: datetime | None = None) -> list[ScheduleData]:
        if now is None:
            now = datetime.now(timezone.utc)

        result = await self._db.execute(
            select(Trip).where(
                Trip.status.in_(["scheduled", "active"]),
            )
        )
        trips = result.scalars().all()

        schedules = []
        for trip in trips:
            elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()

            if elapsed_s < -self.SERVICE_WINDOW_BEFORE_S:
                continue
            if elapsed_s > self.SERVICE_WINDOW_AFTER_S + 7200:
                continue

            stops = await self._load_stop_times(trip.id)
            if not stops:
                continue

            route = await self._db.get(Route, trip.route_id)
            route_name = route.short_name if route else "Unknown"

            schedules.append(ScheduleData(
                trip_id=trip.id,
                route_id=trip.route_id,
                route_short_name=route_name,
                vehicle_label=f"{route_name}-{trip.id:03d}",
                scheduled_start_time=trip.scheduled_start_time,
                stops=stops,
            ))

        return schedules

    async def ensure_vehicles_exist(self, now: datetime | None = None) -> list[Vehicle]:
        schedules = await self.get_current_schedule(now)
        vehicles = []

        for schedule in schedules:
            existing = await self._db.execute(
                select(Vehicle).where(Vehicle.trip_id == schedule.trip_id)
            )
            existing_vehicles = existing.scalars().all()

            if existing_vehicles:
                vehicles.extend(existing_vehicles)
            else:
                vehicle = Vehicle(
                    label=schedule.vehicle_label,
                    route_id=schedule.route_id,
                    trip_id=schedule.trip_id,
                    status="active",
                )
                self._db.add(vehicle)
                await self._db.flush()
                vehicles.append(vehicle)

        return vehicles

    async def _load_stop_times(self, trip_id: int) -> list[StopTimeEntry]:
        result = await self._db.execute(
            select(StopTime)
            .where(StopTime.trip_id == trip_id)
            .order_by(StopTime.sequence)
        )
        stop_times = result.scalars().all()

        entries = []
        for st in stop_times:
            stop = await self._db.get(Stop, st.stop_id)
            if stop is None or stop.location is None:
                continue

            from geoalchemy2.shape import to_shape
            point = to_shape(stop.location)

            entries.append(StopTimeEntry(
                stop_id=st.stop_id,
                sequence=st.sequence,
                arrival_offset_s=st.arrival_offset_s,
                departure_offset_s=st.departure_offset_s,
                lat=point.y,
                lon=point.x,
            ))

        return entries