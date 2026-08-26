import math
from typing import Optional

from app.geospatial.osrm import get_osrm_client, OSRMResult
from app.geospatial.schemas import WalkingResult
from app.core.constants import AVERAGE_WALKING_SPEED_MPS


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


async def walking_distance(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> WalkingResult:
    if from_lat == to_lat and from_lon == to_lon:
        return WalkingResult(
            distance_m=0.0,
            duration_s=0.0,
            source="haversine",
        )

    osrm = await get_osrm_client()
    osrm_result: Optional[OSRMResult] = await osrm.walking_distance(
        from_lat, from_lon, to_lat, to_lon
    )

    if osrm_result:
        return WalkingResult(
            distance_m=osrm_result.distance_m,
            duration_s=osrm_result.duration_s,
            source="osrm",
        )

    distance_m = _haversine_distance(from_lat, from_lon, to_lat, to_lon)
    duration_s = distance_m / AVERAGE_WALKING_SPEED_MPS

    return WalkingResult(
        distance_m=distance_m,
        duration_s=duration_s,
        source="haversine",
    )