from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.geospatial.location_resolver import resolve_location
from app.geospatial.nearby import nearby_stops
from app.geospatial.walking import walking_distance
from app.geospatial.route_geometry import route_geometry
from app.geospatial.schemas import (
    LocationResolutionResult,
    NearbyStop,
    WalkingResult,
    RouteGeometryResult,
)
from app.geospatial.nominatim import close_nominatim_client
from app.geospatial.osrm import close_osrm_client


class GeospatialService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_location(self, text: str) -> LocationResolutionResult:
        return await resolve_location(self.session, text)

    async def nearby_stops(
        self, lat: float, lon: float, radius_m: float = 400.0
    ) -> list[NearbyStop]:
        return await nearby_stops(self.session, lat, lon, radius_m)

    async def walking_distance(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> WalkingResult:
        return await walking_distance(from_lat, from_lon, to_lat, to_lon)

    async def route_geometry(self, route_id: int) -> Optional[RouteGeometryResult]:
        return await route_geometry(self.session, route_id)

    async def close(self):
        await close_nominatim_client()
        await close_osrm_client()


async def get_geospatial_service(session: AsyncSession) -> GeospatialService:
    return GeospatialService(session)