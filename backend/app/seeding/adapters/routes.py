import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.route import Route
from app.db.models.agency import Agency


class RouteAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_routes(self, routes_data: list[dict], agency_key_to_id: dict[str, int]) -> int:
        imported_count = 0
        for route_data in routes_data:
            existing = await self._get_by_short_name(route_data["short_name"])
            agency_key = self._find_agency_key(route_data["agency_id"])
            agency_id = agency_key_to_id.get(agency_key)
            if not agency_id:
                raise ValueError(f"Agency not found for route {route_data['short_name']}: agency_key={agency_key}")

            route_type = self._map_route_type(route_data["short_name"])

            if existing:
                await self._update(existing, route_data, agency_id, route_type)
            else:
                await self._create(route_data, agency_id, route_type)
            imported_count += 1
        await self.session.flush()
        return imported_count

    def _find_agency_key(self, agency_id: str) -> str:
        if agency_id == "357f3aac-1df5-5e69-988c-de1060f37990":
            return "pmta"
        elif agency_id == "a6a26eed-e2e3-5dd9-b5cb-425acd62cac1":
            return "cda_cmta"
        return "unknown"

    def _map_route_type(self, short_name: str) -> str:
        if short_name in ("Red", "Orange", "Blue", "Green"):
            return "metro"
        elif short_name.startswith("FR-") or short_name.startswith("FRB-") or short_name.startswith("FRG-") or short_name.startswith("ST-"):
            return "feeder"
        return "bus"

    async def _get_by_short_name(self, short_name: str) -> Route | None:
        result = await self.session.execute(
            select(Route).where(Route.short_name == short_name)
        )
        return result.scalar_one_or_none()

    async def _create(self, data: dict, agency_id: int, route_type: str) -> Route:
        route = Route(
            agency_id=agency_id,
            short_name=data["short_name"],
            long_name=data.get("long_name"),
            route_type=route_type,
            color=data.get("color"),
            text_color=None,
            path=None,
            geometry_source=None,
            geometry_confidence=None,
        )
        self.session.add(route)
        return route

    async def _update(self, route: Route, data: dict, agency_id: int, route_type: str) -> Route:
        route.agency_id = agency_id
        route.short_name = data["short_name"]
        route.long_name = data.get("long_name")
        route.route_type = route_type
        route.color = data.get("color")
        route.path = None
        route.geometry_source = None
        route.geometry_confidence = None
        return route


async def import_routes(
    session: AsyncSession,
    routes_data: list[dict],
    agency_key_to_id: dict[str, int],
) -> int:
    adapter = RouteAdapter(session)
    return await adapter.import_routes(routes_data, agency_key_to_id)