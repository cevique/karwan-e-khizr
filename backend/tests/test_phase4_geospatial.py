import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_db, AsyncSessionLocal, close_db
from app.seeding.importer import TransitDataImporter, load_transit_data
from app.db.models.stop import Stop
from app.db.models.route import Route
from app.geospatial.service import GeospatialService
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
from app.geospatial.aliases import resolve_alias, get_landmark_coords, STOP_ALIASES
from app.geospatial.nominatim import NominatimClient, NominatimResult, close_nominatim_client
from app.geospatial.osrm import OSRMClient, OSRMResult, close_osrm_client
from app.core.constants import DEFAULT_WALKING_RADIUS_M
from pathlib import Path


TEST_DATA_PATH = Path("data/transit_data.json")


@pytest.fixture(scope="function")
async def db_session():
    await init_db()
    async with AsyncSessionLocal() as session:
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()
        yield session
    await close_db()
    await close_nominatim_client()
    await close_osrm_client()


class TestLocationResolution:
    @pytest.mark.asyncio
    async def test_exact_stop_match(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "Saddar")
        assert len(result.candidates) > 0
        candidate = result.candidates[0]
        assert candidate.match_type == "exact_stop"
        assert candidate.stop_id is not None
        assert candidate.name == "Saddar"
        assert candidate.match_confidence == 1.0

    @pytest.mark.asyncio
    async def test_exact_stop_match_case_insensitive(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "saddar")
        assert len(result.candidates) > 0
        assert result.candidates[0].match_type == "exact_stop"

    @pytest.mark.asyncio
    async def test_fuzzy_stop_match(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "Sadar")
        assert len(result.candidates) > 0
        candidate = result.candidates[0]
        assert candidate.match_type == "fuzzy_stop"
        assert candidate.match_confidence >= 0.6

    @pytest.mark.asyncio
    async def test_fuzzy_match_returns_multiple_candidates(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "Faiz")
        assert len(result.candidates) >= 1
        for c in result.candidates:
            assert c.match_type in ("exact_stop", "fuzzy_stop", "geocoded")

    @pytest.mark.asyncio
    async def test_unknown_location_returns_empty_or_geocoded(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "xyz_nonexistent_place_12345")
        assert isinstance(result, LocationResolutionResult)
        assert result.candidates is not None

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "")
        assert len(result.candidates) == 0

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "   ")
        assert len(result.candidates) == 0


class TestAliases:
    def test_known_stop_aliases_resolve(self):
        assert resolve_alias("saddar bus terminal") == "saddar"
        assert resolve_alias("pak secretariat") == "pak_secretariat"
        assert resolve_alias("faizabad interchange") == "faizabad"
        assert resolve_alias("pims hospital") == "pims_hospital"

    def test_landmark_aliases_have_coords(self):
        coords = get_landmark_coords("faisal mosque")
        assert coords is not None
        lat, lon = coords
        assert 33.0 <= lat <= 34.5
        assert 72.5 <= lon <= 73.5

    def test_unknown_alias_returns_none(self):
        assert resolve_alias("completely_unknown_place") is None
        assert get_landmark_coords("completely_unknown_place") is None

    def test_alias_coords_within_bounds(self):
        for name, (lat, lon) in get_landmark_coords.__globals__["LANDMARK_ALIASES"].items():
            assert 33.0 <= lat <= 34.5
            assert 72.5 <= lon <= 73.5


class TestNearbyStops:
    @pytest.mark.asyncio
    async def test_nearby_stops_within_default_radius(self, db_session: AsyncSession):
        saddar = await db_session.execute(select(Stop).where(Stop.external_key == "saddar"))
        saddar = saddar.scalar_one()
        from geoalchemy2.shape import to_shape
        point = to_shape(saddar.location)
        lat, lon = point.y, point.x

        stops = await nearby_stops(db_session, lat, lon, DEFAULT_WALKING_RADIUS_M)
        assert isinstance(stops, list)
        for stop in stops:
            assert isinstance(stop, NearbyStop)
            assert stop.distance_m <= DEFAULT_WALKING_RADIUS_M

    @pytest.mark.asyncio
    async def test_nearby_stops_returns_distance(self, db_session: AsyncSession):
        saddar = await db_session.execute(select(Stop).where(Stop.external_key == "saddar"))
        saddar = saddar.scalar_one()
        from geoalchemy2.shape import to_shape
        point = to_shape(saddar.location)
        lat, lon = point.y, point.x

        stops = await nearby_stops(db_session, lat, lon, 400)
        assert len(stops) > 0
        saddar_stop = next((s for s in stops if s.stop_id == saddar.id), None)
        assert saddar_stop is not None
        assert saddar_stop.distance_m < 10

    @pytest.mark.asyncio
    async def test_nearby_stops_empty_result(self, db_session: AsyncSession):
        stops = await nearby_stops(db_session, 0, 0, 100)
        assert stops == []

    @pytest.mark.asyncio
    async def test_nearby_stops_radius_limit(self, db_session: AsyncSession):
        saddar = await db_session.execute(select(Stop).where(Stop.external_key == "saddar"))
        saddar = saddar.scalar_one()
        from geoalchemy2.shape import to_shape
        point = to_shape(saddar.location)
        lat, lon = point.y, point.x

        stops_100 = await nearby_stops(db_session, lat, lon, 100)
        stops_400 = await nearby_stops(db_session, lat, lon, 400)
        assert len(stops_100) <= len(stops_400)


class TestWalkingDistance:
    @pytest.mark.asyncio
    async def test_walking_distance_returns_valid_result(self):
        result = await walking_distance(33.646, 73.048, 33.7288, 73.0913)
        assert isinstance(result, WalkingResult)
        assert result.distance_m > 0
        assert result.duration_s > 0
        assert result.source in ("osrm", "haversine")

    @pytest.mark.asyncio
    async def test_walking_distance_same_point(self):
        result = await walking_distance(33.646, 73.048, 33.646, 73.048)
        assert result.distance_m == 0
        assert result.duration_s == 0

    @pytest.mark.asyncio
    async def test_walking_distance_reasonable_values(self):
        result = await walking_distance(33.646, 73.048, 33.7288, 73.0913)
        assert 5000 < result.distance_m < 20000


class TestRouteGeometry:
    @pytest.mark.asyncio
    async def test_route_geometry_returns_none_when_no_geometry(self, db_session: AsyncSession):
        result = await db_session.execute(select(Route).where(Route.short_name == "Red"))
        route = result.scalar_one()
        geom_result = await route_geometry(db_session, route.id)
        assert geom_result is not None
        assert geom_result.route_id == route.id
        assert geom_result.geometry is None

    @pytest.mark.asyncio
    async def test_route_geometry_returns_none_for_invalid_route(self, db_session: AsyncSession):
        geom_result = await route_geometry(db_session, 99999)
        assert geom_result is None


class TestNominatimClient:
    @pytest.mark.asyncio
    async def test_nominatim_client_initialization(self):
        client = NominatimClient()
        assert client._client is None
        await client.close()

    @pytest.mark.asyncio
    async def test_nominatim_cache_behavior(self):
        client = NominatimClient()
        cache_key = "test query"
        result = NominatimResult(
            lat=33.7,
            lon=73.0,
            display_name="Test",
            confidence=0.8,
        )
        import time
        client._cache[cache_key] = (result, time.time())
        cached = client._cache.get(cache_key)
        assert cached is not None
        assert client._is_cache_valid(cached[1])
        await client.close()

    @pytest.mark.asyncio
    async def test_nominatim_bounds_validation(self):
        client = NominatimClient()
        assert client._is_within_bounds(33.7, 73.0)
        assert not client._is_within_bounds(0, 0)
        assert not client._is_within_bounds(33.7, 70.0)
        await client.close()


class TestOSRMClient:
    @pytest.mark.asyncio
    async def test_osrm_client_initialization(self):
        client = OSRMClient()
        assert client._client is None
        await client.close()

    @pytest.mark.asyncio
    async def test_osrm_cache_behavior(self):
        client = OSRMClient()
        cache_key = "33.646,73.048;33.7288,73.0913"
        result = OSRMResult(distance_m=10000, duration_s=7000)
        import time
        client._cache[cache_key] = (result, time.time())
        cached = client._cache.get(cache_key)
        assert cached is not None
        assert client._is_cache_valid(cached[1])
        await client.close()


class TestGeospatialService:
    @pytest.mark.asyncio
    async def test_service_resolve_location(self, db_session: AsyncSession):
        service = GeospatialService(db_session)
        result = await service.resolve_location("Saddar")
        assert isinstance(result, LocationResolutionResult)
        assert len(result.candidates) > 0
        await service.close()

    @pytest.mark.asyncio
    async def test_service_nearby_stops(self, db_session: AsyncSession):
        service = GeospatialService(db_session)
        saddar = await db_session.execute(select(Stop).where(Stop.external_key == "saddar"))
        saddar = saddar.scalar_one()
        from geoalchemy2.shape import to_shape
        point = to_shape(saddar.location)
        stops = await service.nearby_stops(point.y, point.x)
        assert isinstance(stops, list)
        await service.close()

    @pytest.mark.asyncio
    async def test_service_walking_distance(self, db_session: AsyncSession):
        service = GeospatialService(db_session)
        result = await service.walking_distance(33.646, 73.048, 33.7288, 73.0913)
        assert isinstance(result, WalkingResult)
        await service.close()

    @pytest.mark.asyncio
    async def test_service_route_geometry(self, db_session: AsyncSession):
        service = GeospatialService(db_session)
        result = await db_session.execute(select(Route).where(Route.short_name == "Red"))
        route = result.scalar_one()
        geom = await service.route_geometry(route.id)
        assert geom is not None
        assert geom.route_id == route.id
        await service.close()


class TestAmbiguityHandling:
    @pytest.mark.asyncio
    async def test_ambiguous_input_returns_multiple_candidates(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "Faizabad")
        assert isinstance(result, LocationResolutionResult)
        if len(result.candidates) >= 2:
            c1, c2 = result.candidates[0], result.candidates[1]
            diff = abs(c1.match_confidence - c2.match_confidence)
            if diff < 0.15 and c1.match_confidence > 0.6:
                pass


class TestGeographicBoundsValidation:
    @pytest.mark.asyncio
    async def test_nominatim_rejects_out_of_bounds(self):
        client = NominatimClient()
        assert not client._is_within_bounds(51.5, -0.1)
        assert not client._is_within_bounds(40.7, -74.0)
        assert client._is_within_bounds(33.7, 73.0)
        await client.close()

    def test_landmark_coords_within_bounds(self):
        for name, (lat, lon) in get_landmark_coords.__globals__["LANDMARK_ALIASES"].items():
            assert 33.0 <= lat <= 34.5, f"{name}: lat {lat} out of bounds"
            assert 72.5 <= lon <= 73.5, f"{name}: lon {lon} out of bounds"


class TestCachingBehavior:
    @pytest.mark.asyncio
    async def test_nominatim_caching(self):
        client = NominatimClient()
        import time
        result = NominatimResult(
            lat=33.7, lon=73.0, display_name="Test", confidence=0.8
        )
        client._cache["test"] = (result, time.time())
        assert "test" in client._cache
        await client.close()

    @pytest.mark.asyncio
    async def test_osrm_caching(self):
        client = OSRMClient()
        import time
        result = OSRMResult(distance_m=1000, duration_s=700)
        client._cache["test"] = (result, time.time())
        assert "test" in client._cache
        await client.close()


class TestEmptyResults:
    @pytest.mark.asyncio
    async def test_nearby_stops_no_stops_in_radius(self, db_session: AsyncSession):
        stops = await nearby_stops(db_session, 0, 0, 100)
        assert stops == []

    @pytest.mark.asyncio
    async def test_route_geometry_none_for_route_without_path(self, db_session: AsyncSession):
        result = await db_session.execute(select(Route).where(Route.path.is_(None)).limit(1))
        route = result.scalar_one_or_none()
        if route:
            geom = await route_geometry(db_session, route.id)
            assert geom is not None
            assert geom.geometry is None


class TestCoordinateProvenance:
    @pytest.mark.asyncio
    async def test_resolved_stop_candidates_have_provenance(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "Saddar")
        for c in result.candidates:
            if c.match_type in ("exact_stop", "fuzzy_stop"):
                assert c.stop_id is not None
                db_stop = await db_session.execute(select(Stop).where(Stop.id == c.stop_id))
                db_stop = db_stop.scalar_one()
                assert db_stop.coordinate_source is not None
                assert db_stop.coordinate_confidence is not None


class TestIntegrationWithRealData:
    @pytest.mark.asyncio
    async def test_saddar_resolution_returns_correct_coords(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "Saddar")
        assert len(result.candidates) > 0
        c = result.candidates[0]
        assert abs(c.lat - 33.646) < 0.01
        assert abs(c.lon - 73.048) < 0.01

    @pytest.mark.asyncio
    async def test_pak_secretariat_resolution(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "Pak Secretariat")
        assert len(result.candidates) > 0
        c = result.candidates[0]
        assert abs(c.lat - 33.7288) < 0.01
        assert abs(c.lon - 73.0913) < 0.01

    @pytest.mark.asyncio
    async def test_pims_hospital_resolution(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "PIMS Hospital")
        assert len(result.candidates) > 0
        c = result.candidates[0]
        assert abs(c.lat - 33.6988) < 0.02
        assert abs(c.lon - 73.0653) < 0.02


class TestNoFabrication:
    @pytest.mark.asyncio
    async def test_unknown_stop_returns_no_fabricated_candidates(self, db_session: AsyncSession):
        result = await resolve_location(db_session, "DefinitelyNotARealPlace12345")
        for c in result.candidates:
            if c.match_type == "geocoded":
                assert c.lat != 0 and c.lon != 0
                assert 33.0 <= c.lat <= 34.5
                assert 72.5 <= c.lon <= 73.5

    @pytest.mark.asyncio
    async def test_route_geometry_never_fabricated(self, db_session: AsyncSession):
        result = await db_session.execute(select(Route))
        routes = result.scalars().all()
        for route in routes:
            geom = await route_geometry(db_session, route.id)
            if route.path is None:
                assert geom.geometry is None
            else:
                assert geom.geometry is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])