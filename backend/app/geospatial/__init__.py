from app.geospatial.service import GeospatialService, get_geospatial_service
from app.geospatial.schemas import (
    LocationCandidate,
    LocationResolutionResult,
    NearbyStop,
    WalkingResult,
    RouteGeometryResult,
)
from app.geospatial.location_resolver import resolve_location
from app.geospatial.nearby import nearby_stops
from app.geospatial.walking import walking_distance
from app.geospatial.route_geometry import route_geometry
from app.geospatial.aliases import resolve_alias, get_landmark_coords, STOP_ALIASES, LANDMARK_ALIASES
from app.geospatial.nominatim import get_nominatim_client, close_nominatim_client
from app.geospatial.osrm import get_osrm_client, close_osrm_client

__all__ = [
    "GeospatialService",
    "get_geospatial_service",
    "LocationCandidate",
    "LocationResolutionResult",
    "NearbyStop",
    "WalkingResult",
    "RouteGeometryResult",
    "resolve_location",
    "nearby_stops",
    "walking_distance",
    "route_geometry",
    "resolve_alias",
    "get_landmark_coords",
    "STOP_ALIASES",
    "LANDMARK_ALIASES",
    "get_nominatim_client",
    "close_nominatim_client",
    "get_osrm_client",
    "close_osrm_client",
]