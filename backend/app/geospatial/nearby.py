from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import functions as geofunc
from geoalchemy2.shape import to_shape

from app.db.models.stop import Stop
from app.geospatial.schemas import NearbyStop
from app.core.constants import DEFAULT_WALKING_RADIUS_M, MAX_WALKING_RADIUS_M


async def nearby_stops(
    session: AsyncSession,
    lat: float,
    lon: float,
    radius_m: float = DEFAULT_WALKING_RADIUS_M,
) -> list[NearbyStop]:
    radius_m = min(max(radius_m, 1.0), MAX_WALKING_RADIUS_M)

    point_wkt = f"SRID=4326;POINT({lon} {lat})"

    query = (
        select(
            Stop.id,
            Stop.name,
            Stop.location,
            geofunc.ST_Distance(
                Stop.location,
                func.ST_GeogFromText(point_wkt),
            ).label("distance_m"),
        )
        .where(
            geofunc.ST_DWithin(
                Stop.location,
                func.ST_GeogFromText(point_wkt),
                radius_m,
            )
        )
        .order_by("distance_m")
    )

    result = await session.execute(query)
    rows = result.all()

    stops = []
    for row in rows:
        stop_id, name, location, distance_m = row
        point = to_shape(location)
        stops.append(
            NearbyStop(
                stop_id=stop_id,
                name=name,
                lat=point.y,
                lon=point.x,
                distance_m=float(distance_m),
            )
        )

    return stops