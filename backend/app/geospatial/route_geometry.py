from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape
from geojson import Feature, LineString, dumps

from app.db.models.route import Route
from app.geospatial.schemas import RouteGeometryResult


async def route_geometry(session: AsyncSession, route_id: int) -> Optional[RouteGeometryResult]:
    result = await session.execute(
        select(Route).where(Route.id == route_id)
    )
    route = result.scalar_one_or_none()

    if not route:
        return None

    if route.path is None:
        return RouteGeometryResult(
            route_id=route_id,
            geometry=None,
            geometry_source=route.geometry_source,
            geometry_confidence=route.geometry_confidence,
        )

    geom = to_shape(route.path)
    if geom.geom_type != "LineString":
        return RouteGeometryResult(
            route_id=route_id,
            geometry=None,
            geometry_source=route.geometry_source,
            geometry_confidence=route.geometry_confidence,
        )

    coordinates = list(geom.coords)
    geojson = {
        "type": "LineString",
        "coordinates": coordinates,
    }

    return RouteGeometryResult(
        route_id=route_id,
        geometry=geojson,
        geometry_source=route.geometry_source,
        geometry_confidence=route.geometry_confidence,
    )