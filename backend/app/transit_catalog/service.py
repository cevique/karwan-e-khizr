from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.agency import Agency
from app.db.models.route import Route
from app.db.models.stop import Stop
from app.transit_catalog.schemas import (
    RouteListResponse,
    RouteSummary,
    StopListResponse,
    StopSummary,
)


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
        query = select(Stop).where(Stop.location.is_not(None))
        count_query = select(func.count()).select_from(Stop).where(Stop.location.is_not(None))

        if search:
            pattern = f"%{search}%"
            query = query.where(Stop.name.ilike(pattern))
            count_query = count_query.where(Stop.name.ilike(pattern))

        total = (await self.session.execute(count_query)).scalar_one()

        query = query.order_by(Stop.name).limit(limit).offset(offset)
        stops = (await self.session.execute(query)).scalars().all()

        summaries = []
        for stop in stops:
            point = to_shape(stop.location)
            summaries.append(
                StopSummary(
                    id=stop.id,
                    name=stop.name,
                    external_key=stop.external_key,
                    lat=point.y,
                    lon=point.x,
                    zone_id=stop.zone_id,
                    coordinate_confidence=stop.coordinate_confidence,
                )
            )

        return StopListResponse(stops=summaries, total=total, limit=limit, offset=offset)

    async def get_stop(self, stop_id: int) -> StopSummary:
        result = await self.session.execute(select(Stop).where(Stop.id == stop_id))
        stop = result.scalar_one_or_none()
        if stop is None or stop.location is None:
            raise NotFoundError(f"Stop {stop_id} not found")

        point = to_shape(stop.location)
        return StopSummary(
            id=stop.id,
            name=stop.name,
            external_key=stop.external_key,
            lat=point.y,
            lon=point.x,
            zone_id=stop.zone_id,
            coordinate_confidence=stop.coordinate_confidence,
        )
