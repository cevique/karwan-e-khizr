import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_db, AsyncSessionLocal, close_db
from app.seeding.importer import TransitDataImporter, load_transit_data
from app.main import create_app
from app.transit_catalog.service import TransitCatalogService

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


@pytest.fixture(scope="function")
def client(db_session):
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestTransitCatalogServiceRoutes:
    @pytest.mark.asyncio
    async def test_list_routes_returns_seeded_routes(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        result = await service.list_routes()
        assert result.total > 0
        assert len(result.routes) == min(result.total, result.limit)

    @pytest.mark.asyncio
    async def test_list_routes_includes_agency_name_and_color(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        result = await service.list_routes()
        route = result.routes[0]
        assert route.agency_name
        assert route.short_name
        assert route.route_type in ("bus", "metro", "feeder")

    @pytest.mark.asyncio
    async def test_list_routes_filters_by_route_type(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        result = await service.list_routes(route_type="metro")
        assert result.total > 0
        assert all(r.route_type == "metro" for r in result.routes)

    @pytest.mark.asyncio
    async def test_list_routes_pagination(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        full = await service.list_routes(limit=500)
        page1 = await service.list_routes(limit=1, offset=0)
        page2 = await service.list_routes(limit=1, offset=1)
        assert len(page1.routes) == 1
        assert len(page2.routes) == 1
        assert page1.routes[0].id != page2.routes[0].id
        assert page1.total == full.total

    @pytest.mark.asyncio
    async def test_get_route_by_id(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        listing = await service.list_routes(limit=1)
        route_id = listing.routes[0].id
        route = await service.get_route(route_id)
        assert route.id == route_id

    @pytest.mark.asyncio
    async def test_get_route_not_found_raises(self, db_session: AsyncSession):
        from app.core.exceptions import NotFoundError

        service = TransitCatalogService(db_session)
        with pytest.raises(NotFoundError):
            await service.get_route(999_999_999)


class TestTransitCatalogServiceStops:
    @pytest.mark.asyncio
    async def test_list_stops_returns_seeded_stops(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        result = await service.list_stops()
        assert result.total > 0
        assert len(result.stops) == min(result.total, result.limit)

    @pytest.mark.asyncio
    async def test_list_stops_have_valid_coordinates(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        result = await service.list_stops(limit=20)
        for stop in result.stops:
            assert 33.0 <= stop.lat <= 34.5
            assert 72.5 <= stop.lon <= 73.5

    @pytest.mark.asyncio
    async def test_list_stops_search_filter(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        result = await service.list_stops(search="saddar")
        assert result.total > 0
        assert all("saddar" in s.name.lower() for s in result.stops)

    @pytest.mark.asyncio
    async def test_get_stop_by_id(self, db_session: AsyncSession):
        service = TransitCatalogService(db_session)
        listing = await service.list_stops(limit=1)
        stop_id = listing.stops[0].id
        stop = await service.get_stop(stop_id)
        assert stop.id == stop_id

    @pytest.mark.asyncio
    async def test_get_stop_not_found_raises(self, db_session: AsyncSession):
        from app.core.exceptions import NotFoundError

        service = TransitCatalogService(db_session)
        with pytest.raises(NotFoundError):
            await service.get_stop(999_999_999)


class TestTransitCatalogEndpointsHTTP:
    def test_get_routes_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/transit/routes")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] > 0
        assert len(body["routes"]) > 0

    def test_get_routes_respects_limit(self, client: TestClient):
        resp = client.get("/api/v1/transit/routes?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()["routes"]) == 2

    def test_get_route_detail_returns_200(self, client: TestClient):
        listing = client.get("/api/v1/transit/routes?limit=1").json()
        route_id = listing["routes"][0]["id"]
        resp = client.get(f"/api/v1/transit/routes/{route_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == route_id

    def test_get_route_detail_404(self, client: TestClient):
        resp = client.get("/api/v1/transit/routes/999999999")
        assert resp.status_code == 404

    def test_get_stops_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/transit/stops")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] > 0
        assert len(body["stops"]) > 0

    def test_get_stop_detail_returns_200(self, client: TestClient):
        listing = client.get("/api/v1/transit/stops?limit=1").json()
        stop_id = listing["stops"][0]["id"]
        resp = client.get(f"/api/v1/transit/stops/{stop_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == stop_id

    def test_get_stop_detail_404(self, client: TestClient):
        resp = client.get("/api/v1/transit/stops/999999999")
        assert resp.status_code == 404

    def test_invalid_route_type_returns_422(self, client: TestClient):
        resp = client.get("/api/v1/transit/routes?route_type=nonexistent_type")
        assert resp.status_code == 422
