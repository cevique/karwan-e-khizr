import json
from pathlib import Path
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.seeding.adapters.agencies import import_agencies
from app.seeding.adapters.routes import import_routes
from app.seeding.adapters.stops import import_stops
from app.seeding.adapters.route_stops import import_route_stops
from app.seeding.adapters.trips import import_trips
from app.seeding.adapters.stop_times import import_stop_times
from app.seeding.adapters.fare_rules import import_fare_rules
from app.db.models.agency import Agency
from app.db.models.route import Route
from app.db.models.stop import Stop
from sqlalchemy import select


class TransitDataImporter:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.route_key_to_id: dict[str, int] = {}
        self.stop_key_to_id: dict[str, int] = {}
        self.agency_key_to_id: dict[str, int] = {}
        self.stop_uuid_to_key: dict[str, str] = {}

    async def import_all(self, data: dict[str, Any]) -> dict[str, int]:
        results = {}

        results["agencies"] = await self._import_agencies(data.get("operators", []))
        await self._build_agency_key_map()

        results["stops"] = await self._import_stops(data.get("stops", []))
        await self._build_stop_key_maps(data.get("stops", []))

        results["routes"] = await self._import_routes(data.get("routes", []))
        await self._build_route_key_map()

        results["route_stops"] = await self._import_route_stops(data.get("route_stops", []))

        results["trips"] = await self._import_trips(data.get("trips", []))

        results["stop_times"] = await self._import_stop_times(data.get("trips", []))

        results["fare_rules"] = await self._import_fare_rules(
            data.get("fare_rules") or self._get_default_fare_rules()
        )

        return results

    async def _import_agencies(self, agencies_data: list[dict]) -> int:
        return await import_agencies(self.session, agencies_data)

    async def _import_stops(self, stops_data: list[dict]) -> int:
        return await import_stops(self.session, stops_data)

    async def _import_routes(self, routes_data: list[dict]) -> int:
        return await import_routes(self.session, routes_data, self.agency_key_to_id)

    async def _import_route_stops(self, route_stops_data: list[dict]) -> int:
        return await import_route_stops(
            self.session, route_stops_data, self.route_key_to_id, self.stop_key_to_id, self.stop_uuid_to_key
        )

    async def _import_trips(self, trips_data: list[dict]) -> int:
        return await import_trips(self.session, trips_data, self.route_key_to_id)

    async def _import_stop_times(self, trips_data: list[dict]) -> int:
        return await import_stop_times(
            self.session, trips_data, self.route_key_to_id, self.stop_key_to_id, self.stop_uuid_to_key
        )

    async def _import_fare_rules(self, fare_rules_data: list[dict]) -> int:
        return await import_fare_rules(self.session, fare_rules_data)

    async def _build_agency_key_map(self) -> None:
        result = await self.session.execute(select(Agency))
        for agency in result.scalars().all():
            self.agency_key_to_id[agency.short_name] = agency.id

    async def _build_stop_key_maps(self, stops_data: list[dict]) -> None:
        result = await self.session.execute(select(Stop))
        for stop in result.scalars().all():
            if stop.external_key:
                self.stop_key_to_id[stop.external_key] = stop.id
        for stop_data in stops_data:
            self.stop_uuid_to_key[stop_data["id"]] = stop_data["key"]

    async def _build_route_key_map(self) -> None:
        result = await self.session.execute(select(Route))
        for route in result.scalars().all():
            self.route_key_to_id[route.short_name] = route.id

    def _get_default_fare_rules(self) -> list[dict]:
        return [
            {
                "name": "Standard Metrobus",
                "base_fare": 50.0,
                "per_leg_fare": 20.0,
                "currency": "PKR",
                "is_active": True,
            },
            {
                "name": "Feeder Route",
                "base_fare": 30.0,
                "per_leg_fare": 15.0,
                "currency": "PKR",
                "is_active": True,
            },
        ]


def load_transit_data(file_path: str | Path) -> dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)