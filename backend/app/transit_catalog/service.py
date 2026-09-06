import httpx
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.agency import Agency
from app.db.models.route import Route
from app.db.models.route_stop import RouteStop
from app.db.models.stop import Stop
from app.transit_catalog.schemas import (
    RouteGeometryResponse,
    RouteListResponse,
    RouteStopItem,
    RouteStopsResponse,
    RouteSummary,
    StopListResponse,
    StopSummary,
)

# Simple in-memory cache for route geometries (route_id -> coordinates)
_geometry_cache: dict[int, list[list[float]]] = {}


class TransitCatalogService:
    """Read-only listing/detail access to the routes and stops master data.

    This is reference data (names, colors, coordinates) seeded from the
    transit dataset - it changes rarely, unlike vehicle positions or
    journeys. Kept intentionally simple (list + get by id) since it's
    expected to grow (filtering, agency scoping, pagination tuning) as the
    dataset expands.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_routes(
        self,
        route_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> RouteListResponse:
        query = select(Route, Agency.name).join(Agency, Route.agency_id == Agency.id)
        count_query = select(func.count()).select_from(Route)

        if route_type is not None:
            query = query.where(Route.route_type == route_type)
            count_query = count_query.where(Route.route_type == route_type)

        total = (await self.session.execute(count_query)).scalar_one()

        query = query.order_by(Route.short_name).limit(limit).offset(offset)
        rows = (await self.session.execute(query)).all()

        summaries = [
            RouteSummary(
                id=route.id,
                agency_id=route.agency_id,
                agency_name=agency_name,
                short_name=route.short_name,
                long_name=route.long_name,
                route_type=route.route_type,
                color=route.color,
                text_color=route.text_color,
                has_geometry=route.path is not None,
            )
            for route, agency_name in rows
        ]

        return RouteListResponse(routes=summaries, total=total, limit=limit, offset=offset)

    async def get_route(self, route_id: int) -> RouteSummary:
        result = await self.session.execute(
            select(Route, Agency.name)
            .join(Agency, Route.agency_id == Agency.id)
            .where(Route.id == route_id)
        )
        row = result.first()
        if row is None:
            raise NotFoundError(f"Route {route_id} not found")

        route, agency_name = row
        return RouteSummary(
            id=route.id,
            agency_id=route.agency_id,
            agency_name=agency_name,
            short_name=route.short_name,
            long_name=route.long_name,
            route_type=route.route_type,
            color=route.color,
            text_color=route.text_color,
            has_geometry=route.path is not None,
        )

    async def list_stops(
        self,
        search: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> StopListResponse:
        query = select(Stop)
        count_query = select(func.count()).select_from(Stop)

        if search:
            pattern = f"%{search}%"
            query = query.where(Stop.name.ilike(pattern))
            count_query = count_query.where(Stop.name.ilike(pattern))

        total = (await self.session.execute(count_query)).scalar_one()

        query = query.order_by(Stop.name).limit(limit).offset(offset)
        stops = (await self.session.execute(query)).scalars().all()

        summaries = []
        for stop in stops:
            lat = None
            lon = None
            if stop.location is not None:
                point = to_shape(stop.location)
                lat = point.y
                lon = point.x
            summaries.append(
                StopSummary(
                    id=stop.id,
                    name=stop.name,
                    external_key=stop.external_key,
                    lat=lat,
                    lon=lon,
                    zone_id=stop.zone_id,
                    coordinate_confidence=stop.coordinate_confidence,
                )
            )

        return StopListResponse(stops=summaries, total=total, limit=limit, offset=offset)

    async def get_stop(self, stop_id: int) -> StopSummary:
        result = await self.session.execute(select(Stop).where(Stop.id == stop_id))
        stop = result.scalar_one_or_none()
        if stop is None:
            raise NotFoundError(f"Stop {stop_id} not found")

        lat = None
        lon = None
        if stop.location is not None:
            point = to_shape(stop.location)
            lat = point.y
            lon = point.x
        return StopSummary(
            id=stop.id,
            name=stop.name,
            external_key=stop.external_key,
            lat=lat,
            lon=lon,
            zone_id=stop.zone_id,
            coordinate_confidence=stop.coordinate_confidence,
        )

    async def get_route_stops(self, route_id: int) -> RouteStopsResponse:
        route_result = await self.session.execute(
            select(Route).where(Route.id == route_id)
        )
        route = route_result.scalar_one_or_none()
        if route is None:
            raise NotFoundError(f"Route {route_id} not found")

        query = (
            select(RouteStop, Stop)
            .join(Stop, RouteStop.stop_id == Stop.id)
            .where(RouteStop.route_id == route_id)
            .order_by(RouteStop.sequence)
        )
        rows = (await self.session.execute(query)).all()

        stops = []
        for route_stop, stop in rows:
            lat = None
            lon = None
            if stop.location is not None:
                point = to_shape(stop.location)
                lat = point.y
                lon = point.x
            stops.append(
                RouteStopItem(
                    stop_id=stop.id,
                    stop_name=stop.name,
                    lat=lat,
                    lon=lon,
                    sequence=route_stop.sequence,
                )
            )

        return RouteStopsResponse(
            route_id=route.id,
            route_name=route.long_name or route.short_name,
            color=route.color,
            stops=stops,
        )

    async def get_route_geometry(self, route_id: int) -> RouteGeometryResponse:
        """Fetch road-following geometry from OSRM for a route's stops."""
        if route_id in _geometry_cache:
            return RouteGeometryResponse(
                route_id=route_id,
                coordinates=_geometry_cache[route_id],
            )

        stops_resp = await self.get_route_stops(route_id)
        valid_stops = [(s.lon, s.lat) for s in stops_resp.stops if s.lat is not None and s.lon is not None]

        if len(valid_stops) < 2:
            return RouteGeometryResponse(route_id=route_id, coordinates=[])

        coords_str = ";".join(f"{lon},{lat}" for lon, lat in valid_stops)
        url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code") == "Ok" and data.get("routes"):
                coords = data["routes"][0]["geometry"]["coordinates"]
                _geometry_cache[route_id] = coords
                return RouteGeometryResponse(route_id=route_id, coordinates=coords)
        except Exception:
            pass

        # Fallback to straight lines
        coords = [list(c) for c in valid_stops]
        _geometry_cache[route_id] = coords
        return RouteGeometryResponse(route_id=route_id, coordinates=coords)
