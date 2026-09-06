from __future__ import annotations

import httpx
from datetime import datetime, timezone
from typing import Optional, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.route import Route
from app.db.models.route_stop import RouteStop
from app.db.models.stop import Stop
from app.db.models.stop_time import StopTime
from app.db.models.trip import Trip
from app.db.models.vehicle import Vehicle
from app.db.models.vehicle_position import VehiclePosition as VehiclePositionModel
from app.eta.predictor import ETAPredictor, NoOpETAPredictor
from app.eta.features import extract_eta_features
from app.simulation.engine import SimulationEngine
from app.simulation.schemas import StopTimeEntry

# In-memory cache for OSRM route geometry
_geometry_cache: dict[int, list[tuple[float, float]]] = {}


async def _fetch_route_geometry(route_id: int) -> list[tuple[float, float]]:
    """Fetch road-following geometry from OSRM for a route's stops."""
    if route_id in _geometry_cache:
        return _geometry_cache[route_id]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get route stops from the transit catalog service
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                query = (
                    select(RouteStop, Stop)
                    .join(Stop, RouteStop.stop_id == Stop.id)
                    .where(RouteStop.route_id == route_id)
                    .order_by(RouteStop.sequence)
                )
                rows = (await session.execute(query)).all()
                stops = []
                for rs, stop in rows:
                    if stop.location is not None:
                        from geoalchemy2.shape import to_shape
                        point = to_shape(stop.location)
                        stops.append((point.x, point.y))  # (lon, lat)

            if len(stops) < 2:
                return []

            coords_str = ";".join(f"{lon},{lat}" for lon, lat in stops)
            url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == "Ok" and data.get("routes"):
                coords = [
                    (c[1], c[0]) for c in data["routes"][0]["geometry"]["coordinates"]
                ]
                _geometry_cache[route_id] = coords
                return coords
    except Exception:
        pass

    # Fallback to straight-line stop coordinates
    try:
        async with AsyncSessionLocal() as session:
            query = (
                select(RouteStop, Stop)
                .join(Stop, RouteStop.stop_id == Stop.id)
                .where(RouteStop.route_id == route_id)
                .order_by(RouteStop.sequence)
            )
            rows = (await session.execute(query)).all()
            coords = []
            for rs, stop in rows:
                if stop.location is not None:
                    from geoalchemy2.shape import to_shape
                    point = to_shape(stop.location)
                    coords.append((point.x, point.y))
            _geometry_cache[route_id] = coords
            return coords
    except Exception:
        return []


class VehicleLocationProvider(Protocol):
    async def get_all_positions(self) -> list[dict]: ...
    async def get_vehicle_position(self, vehicle_id: int) -> Optional[dict]: ...
    async def get_vehicle_eta(self, vehicle_id: int) -> Optional[dict]: ...


class SimulatedVehicleLocationProvider:
    """Default implementation using SimulationEngine and DB schedule data."""

    def __init__(
        self,
        engine: SimulationEngine,
        db: AsyncSession,
        eta_predictor: Optional[ETAPredictor] = None,
    ):
        self._engine = engine
        self._db = db
        self._eta_predictor = eta_predictor or NoOpETAPredictor()

    async def get_all_positions(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        trips = await self._load_active_trips(now)
        results = []
        for trip_info in trips:
            pos = await self._compute_vehicle_position(trip_info, now)
            if pos is not None:
                results.append(pos)
        return results

    async def get_vehicle_position(self, vehicle_id: int) -> Optional[dict]:
        now = datetime.now(timezone.utc)
        vehicle = await self._db.get(Vehicle, vehicle_id)
        if vehicle is None or vehicle.trip_id is None:
            return None

        trip = await self._db.get(Trip, vehicle.trip_id)
        if trip is None:
            return None

        stops = await self._load_stop_times(trip.id)
        if not stops:
            return None

        route = await self._db.get(Route, trip.route_id)
        route_name = route.short_name if route else "Unknown"

        elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
        total_duration = stops[-1].arrival_offset_s + SimulationEngine.DEFAULT_DWELL_S
        if total_duration > 0:
            elapsed_s = elapsed_s % total_duration
        geometry = await _fetch_route_geometry(trip.route_id)
        pos_data = self._engine.compute_position_at(stops, elapsed_s, route_geometry=geometry if geometry else None)

        return {
            "id": vehicle.id,
            "label": vehicle.label,
            "route_id": trip.route_id,
            "trip_id": trip.id,
            "latitude": pos_data["latitude"],
            "longitude": pos_data["longitude"],
            "bearing": pos_data["bearing"],
            "speed": pos_data["speed"],
            "status": vehicle.status,
            "source": "simulated",
            "timestamp": now,
            "next_stop_id": pos_data["next_stop_id"],
            "eta_seconds": pos_data["eta_seconds"],
        }

    async def get_vehicle_eta(self, vehicle_id: int) -> Optional[dict]:
        now = datetime.now(timezone.utc)
        vehicle = await self._db.get(Vehicle, vehicle_id)
        if vehicle is None or vehicle.trip_id is None:
            return None

        trip = await self._db.get(Trip, vehicle.trip_id)
        if trip is None:
            return None

        stops = await self._load_stop_times(trip.id)
        if not stops:
            return None

        elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
        eta_data = self._engine.compute_eta_at(stops, elapsed_s)
        if eta_data is None:
            return None

        # Attempt ML prediction via ETAPredictor
        predicted_eta = None
        if self._eta_predictor.is_available:
            features = extract_eta_features(
                stops=stops,
                current_elapsed_s=elapsed_s,
                route_id=trip.route_id,
                current_time=now,
            )
            if features is not None:
                prediction = self._eta_predictor.predict(features)
                if prediction is not None:
                    predicted_eta = int(prediction.predicted_eta_seconds)

        return {
            "vehicle_id": vehicle_id,
            "next_stop_id": eta_data["next_stop_id"],
            "baseline_eta_seconds": eta_data["baseline_eta_seconds"],
            "predicted_eta_seconds": predicted_eta,
            "delay_seconds": None,
            "source": "simulated",
        }

    async def _load_active_trips(self, now: datetime) -> list[dict]:
        result = await self._db.execute(
            select(Trip).where(
                Trip.status.in_(["scheduled", "active"]),
                Trip.scheduled_start_time <= now,
            )
        )
        trips = result.scalars().all()

        active_trips = []
        for trip in trips:
            stops = await self._load_stop_times(trip.id)
            if not stops:
                continue

            elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
            total_duration = stops[-1].arrival_offset_s + SimulationEngine.DEFAULT_DWELL_S

            if elapsed_s < -300:
                continue

            route = await self._db.get(Route, trip.route_id)
            route_name = route.short_name if route else "Unknown"

            vehicles = await self._get_or_create_vehicle(trip, route_name)
            geometry = await _fetch_route_geometry(trip.route_id)
            for vehicle in vehicles:
                active_trips.append({
                    "vehicle": vehicle,
                    "trip": trip,
                    "route_name": route_name,
                    "stops": stops,
                    "total_duration": total_duration,
                    "geometry": geometry,
                })

        # Commit any newly created vehicles so they persist across requests
        if active_trips:
            await self._db.commit()

        return active_trips

    async def _get_or_create_vehicle(self, trip: Trip, route_name: str) -> list[Vehicle]:
        result = await self._db.execute(
            select(Vehicle).where(Vehicle.trip_id == trip.id)
        )
        vehicles = result.scalars().all()

        if not vehicles:
            vehicle = Vehicle(
                label=f"{route_name}-{trip.id:03d}",
                route_id=trip.route_id,
                trip_id=trip.id,
                status="active",
            )
            self._db.add(vehicle)
            await self._db.flush()
            return [vehicle]

        return vehicles

    async def _compute_vehicle_position(self, trip_info: dict, now: datetime) -> Optional[dict]:
        vehicle = trip_info["vehicle"]
        trip = trip_info["trip"]
        stops = trip_info["stops"]
        route_name = trip_info["route_name"]
        total_duration = trip_info["total_duration"]
        geometry = trip_info.get("geometry", [])

        elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
        # Loop the trip: when elapsed exceeds total_duration, wrap around
        if total_duration > 0:
            elapsed_s = elapsed_s % total_duration
        pos_data = self._engine.compute_position_at(stops, elapsed_s, route_geometry=geometry if geometry else None)

        return {
            "id": vehicle.id,
            "label": vehicle.label,
            "route_id": trip.route_id,
            "trip_id": trip.id,
            "latitude": pos_data["latitude"],
            "longitude": pos_data["longitude"],
            "bearing": pos_data["bearing"],
            "speed": pos_data["speed"],
            "status": vehicle.status,
            "source": "simulated",
            "timestamp": now,
            "next_stop_id": pos_data["next_stop_id"],
            "eta_seconds": pos_data["eta_seconds"],
        }

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