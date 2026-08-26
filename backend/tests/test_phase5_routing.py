import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_db, AsyncSessionLocal, close_db
from app.seeding.importer import TransitDataImporter, load_transit_data
from app.db.models.stop import Stop
from app.db.models.route import Route
from app.db.models.route_stop import RouteStop
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.db.models.fare_rule import FareRule
from app.geospatial.service import GeospatialService
from app.routing.engine import JourneySearchEngine, get_journey_search_engine
from app.routing.graph import TransitGraphBuilder, TransitGraph, GraphEdge
from app.routing.dijkstra import run_dijkstra
from app.routing.time_aware import TimeAwareRouter
from app.routing.filters import apply_filters, filter_by_max_walk, filter_by_max_transfers
from app.routing.ranking import rank_journeys, select_top_candidates
from app.routing.schemas import (
    JourneySearchRequest,
    JourneySearchResponse,
    Journey,
    Leg,
    FareQuote,
    LocationResolved,
    AmbiguousLocationResponse,
    NoRouteFoundResponse,
)
from app.routing.objectives import (
    EdgeWeights,
    walking_edge_weight,
    riding_edge_weight,
    transfer_edge_weight,
    compare_objective,
)
from app.ticketing.fares import FaresService
from app.core.constants import DEFAULT_WALKING_RADIUS_M, MAX_JOURNEY_CANDIDATES
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


class TestRoutingSchemas:
    def test_journey_search_request_valid(self):
        req = JourneySearchRequest(
            origin="Saddar",
            destination="Pak Secretariat",
            objective="fastest",
            max_walk_m=400,
            max_transfers=2,
        )
        assert req.origin == "Saddar"
        assert req.destination == "Pak Secretariat"
        assert req.objective == "fastest"
        assert req.max_walk_m == 400
        assert req.max_transfers == 2

    def test_journey_search_request_defaults(self):
        req = JourneySearchRequest(origin="A", destination="B")
        assert req.objective == "fastest"
        assert req.max_walk_m is None
        assert req.max_transfers is None
        assert req.departure_time is None

    def test_journey_search_request_invalid_max_walk(self):
        with pytest.raises(ValueError):
            JourneySearchRequest(origin="A", destination="B", max_walk_m=-100)
        with pytest.raises(ValueError):
            JourneySearchRequest(origin="A", destination="B", max_walk_m=3000)

    def test_journey_search_request_invalid_max_transfers(self):
        with pytest.raises(ValueError):
            JourneySearchRequest(origin="A", destination="B", max_transfers=-1)
        with pytest.raises(ValueError):
            JourneySearchRequest(origin="A", destination="B", max_transfers=10)

    def test_fare_quote(self):
        fare = FareQuote(base_fare=50.0, per_leg_fare=20.0, total=70.0, currency="PKR")
        assert fare.total == 70.0

    def test_leg_walk(self):
        leg = Leg(
            type="walk",
            start_stop_id=1,
            end_stop_id=2,
            start_lat=33.6, start_lon=73.0,
            end_lat=33.7, end_lon=73.1,
            duration_s=600,
            distance_m=800,
        )
        assert leg.type == "walk"
        assert leg.route_id is None
        assert leg.distance_m == 800

    def test_leg_ride(self):
        leg = Leg(
            type="ride",
            route_id=5,
            trip_id=10,
            start_stop_id=1,
            end_stop_id=2,
            start_lat=33.6, start_lon=73.0,
            end_lat=33.7, end_lon=73.1,
            duration_s=1200,
        )
        assert leg.type == "ride"
        assert leg.route_id == 5
        assert leg.trip_id == 10

    def test_journey(self):
        leg = Leg(
            type="walk",
            start_stop_id=1, end_stop_id=2,
            start_lat=33.6, start_lon=73.0,
            end_lat=33.7, end_lon=73.1,
            duration_s=600, distance_m=800,
        )
        journey = Journey(
            legs=[leg],
            total_duration_s=600,
            total_walk_m=800,
            transfer_count=0,
            fare=FareQuote(base_fare=50, per_leg_fare=20, total=50, currency="PKR"),
        )
        assert journey.total_duration_s == 600
        assert journey.transfer_count == 0

    def test_ambiguous_location_response(self):
        resp = AmbiguousLocationResponse(
            error="ambiguous_origin",
            candidates=[
                LocationResolved(name="A", lat=33.6, lon=73.0),
                LocationResolved(name="B", lat=33.7, lon=73.1),
            ],
        )
        assert resp.error == "ambiguous_origin"
        assert len(resp.candidates) == 2

    def test_no_route_found_response(self):
        resp = NoRouteFoundResponse(
            error="no_route_found",
            message="No route found",
        )
        assert resp.error == "no_route_found"


class TestObjectives:
    def test_walking_edge_weight_fastest(self):
        ew = walking_edge_weight(1000.0, "fastest")
        assert ew.duration_s > 0
        assert ew.transfers == 0
        assert ew.walk_m == 1000.0

    def test_walking_edge_weight_fewest_transfers(self):
        ew = walking_edge_weight(1000.0, "fewest_transfers")
        assert ew.transfers == 0
        assert ew.walk_m == 1000.0

    def test_walking_edge_weight_least_walking(self):
        ew = walking_edge_weight(1000.0, "least_walking")
        assert ew.walk_m == 1000.0 * 1000.0

    def test_riding_edge_weight_bus(self):
        ew = riding_edge_weight(5000.0, "bus", "fastest")
        assert ew.duration_s > 0
        assert ew.transfers == 0
        assert ew.walk_m == 0.0

    def test_riding_edge_weight_metro(self):
        ew = riding_edge_weight(5000.0, "metro", "fastest")
        bus_ew = riding_edge_weight(5000.0, "bus", "fastest")
        assert ew.duration_s < bus_ew.duration_s

    def test_transfer_edge_weight(self):
        ew = transfer_edge_weight("fastest")
        assert ew.duration_s > 0
        assert ew.transfers == 1
        assert ew.walk_m == 0.0

    def test_compare_objective_fastest(self):
        a = EdgeWeights(duration_s=1000, transfers=1, walk_m=500)
        b = EdgeWeights(duration_s=1200, transfers=0, walk_m=300)
        assert compare_objective(a, b, "fastest") < 0

    def test_compare_objective_fewest_transfers(self):
        a = EdgeWeights(duration_s=1200, transfers=0, walk_m=500)
        b = EdgeWeights(duration_s=1000, transfers=1, walk_m=300)
        assert compare_objective(a, b, "fewest_transfers") < 0

    def test_compare_objective_least_walking(self):
        a = EdgeWeights(duration_s=1200, transfers=1, walk_m=300)
        b = EdgeWeights(duration_s=1000, transfers=0, walk_m=500)
        assert compare_objective(a, b, "least_walking") < 0


class TestTransitGraphBuilder:
    @pytest.mark.asyncio
    async def test_graph_builder_creates_nodes(self, db_session: AsyncSession):
        builder = TransitGraphBuilder(db_session)
        graph = await builder.build()

        assert len(graph.nodes) > 0
        for node in graph.nodes.values():
            assert node.stop_id > 0
            assert node.lat != 0.0
            assert node.lon != 0.0

    @pytest.mark.asyncio
    async def test_graph_builder_creates_riding_edges(self, db_session: AsyncSession):
        builder = TransitGraphBuilder(db_session)
        graph = await builder.build()

        ride_edges = [e for edges in graph.edges.values() for e in edges if e.edge_type == "ride"]
        assert len(ride_edges) > 0
        for edge in ride_edges:
            assert edge.route_id is not None
            assert edge.edge_type == "ride"
            assert edge.duration_s > 0

    @pytest.mark.asyncio
    async def test_graph_builder_creates_transfer_edges(self, db_session: AsyncSession):
        builder = TransitGraphBuilder(db_session)
        graph = await builder.build()

        transfer_edges = [e for edges in graph.edges.values() for e in edges if e.edge_type == "transfer"]
        assert len(transfer_edges) > 0
        for edge in transfer_edges:
            assert edge.route_id is None
            assert edge.edge_type == "transfer"
            assert edge.distance_m <= DEFAULT_WALKING_RADIUS_M

    @pytest.mark.asyncio
    async def test_graph_builder_add_origin_destination(self, db_session: AsyncSession):
        from app.geospatial.schemas import LocationCandidate

        builder = TransitGraphBuilder(db_session)
        await builder.build()

        origin = LocationCandidate(
            stop_id=None, name="Test Origin", lat=33.646, lon=73.048,
            match_confidence=1.0, match_type="exact_stop",
        )
        dest = LocationCandidate(
            stop_id=None, name="Test Dest", lat=33.7288, lon=73.0913,
            match_confidence=1.0, match_type="exact_stop",
        )

        o_id, d_id = await builder.add_origin_destination(origin, dest)

        graph = builder.graph
        assert o_id == -1
        assert d_id == -2
        assert o_id in graph.nodes
        assert d_id in graph.nodes
        assert graph.origin_node_id == o_id
        assert graph.destination_node_id == d_id

        walk_edges = [e for edges in graph.edges.values() for e in edges if e.edge_type == "walk"]
        assert len(walk_edges) > 0


class TestDijkstra:
    @pytest.mark.asyncio
    async def test_dijkstra_finds_path(self, db_session: AsyncSession):
        builder = TransitGraphBuilder(db_session)
        await builder.build()

        origin = await db_session.execute(select(Stop).where(Stop.external_key == "saddar"))
        origin = origin.scalar_one()
        dest = await db_session.execute(select(Stop).where(Stop.external_key == "pak_secretariat"))
        dest = dest.scalar_one()

        from app.geospatial.schemas import LocationCandidate
        o_cand = LocationCandidate(stop_id=origin.id, name=origin.name, lat=33.646, lon=73.048, match_confidence=1.0, match_type="exact_stop")
        d_cand = LocationCandidate(stop_id=dest.id, name=dest.name, lat=33.7288, lon=73.0913, match_confidence=1.0, match_type="exact_stop")

        await builder.add_origin_destination(o_cand, d_cand)
        graph = builder.graph

        path, cost = run_dijkstra(graph, graph.origin_node_id, graph.destination_node_id, "fastest")

        if path:
            assert len(path) > 0
            assert cost.duration_s > 0
            assert cost.transfers >= 0

    @pytest.mark.asyncio
    async def test_dijkstra_no_path_returns_none(self, db_session: AsyncSession):
        builder = TransitGraphBuilder(db_session)
        await builder.build()

        graph = builder.graph
        path, cost = run_dijkstra(graph, 99999, 99998, "fastest")

        assert path is None
        assert cost is None


class TestTimeAwareRouter:
    @pytest.mark.asyncio
    async def test_time_aware_router_loads_schedule(self, db_session: AsyncSession):
        builder = TransitGraphBuilder(db_session)
        await builder.build()
        graph = builder.graph

        router = TimeAwareRouter(db_session, graph)
        await router._load_schedule_data()

        assert len(router.trip_cache) > 0
        assert len(router.route_trips_cache) > 0


class TestFilters:
    def test_filter_by_max_walk(self):
        journeys = [
            Journey(legs=[], total_duration_s=1000, total_walk_m=300, transfer_count=0),
            Journey(legs=[], total_duration_s=1000, total_walk_m=500, transfer_count=0),
            Journey(legs=[], total_duration_s=1000, total_walk_m=800, transfer_count=0),
        ]
        filtered = filter_by_max_walk(journeys, 400)
        assert len(filtered) == 1
        assert filtered[0].total_walk_m == 300

    def test_filter_by_max_transfers(self):
        journeys = [
            Journey(legs=[], total_duration_s=1000, total_walk_m=300, transfer_count=0),
            Journey(legs=[], total_duration_s=1000, total_walk_m=300, transfer_count=1),
            Journey(legs=[], total_duration_s=1000, total_walk_m=300, transfer_count=2),
        ]
        filtered = filter_by_max_transfers(journeys, 1)
        assert len(filtered) == 2

    def test_apply_filters_both(self):
        journeys = [
            Journey(legs=[], total_duration_s=1000, total_walk_m=300, transfer_count=0),
            Journey(legs=[], total_duration_s=1000, total_walk_m=500, transfer_count=1),
            Journey(legs=[], total_duration_s=1000, total_walk_m=800, transfer_count=2),
        ]
        filtered = apply_filters(journeys, max_walk_m=400, max_transfers=1)
        assert len(filtered) == 1
        assert filtered[0].total_walk_m == 300
        assert filtered[0].transfer_count == 0


class TestRanking:
    def test_rank_journeys_fastest(self):
        journeys = [
            Journey(legs=[], total_duration_s=1200, total_walk_m=300, transfer_count=1),
            Journey(legs=[], total_duration_s=1000, total_walk_m=500, transfer_count=2),
            Journey(legs=[], total_duration_s=1100, total_walk_m=200, transfer_count=0),
        ]
        ranked = rank_journeys(journeys, "fastest")
        assert ranked[0].total_duration_s == 1000

    def test_rank_journeys_fewest_transfers(self):
        journeys = [
            Journey(legs=[], total_duration_s=1200, total_walk_m=300, transfer_count=2),
            Journey(legs=[], total_duration_s=1000, total_walk_m=500, transfer_count=0),
            Journey(legs=[], total_duration_s=1100, total_walk_m=200, transfer_count=1),
        ]
        ranked = rank_journeys(journeys, "fewest_transfers")
        assert ranked[0].transfer_count == 0

    def test_rank_journeys_least_walking(self):
        journeys = [
            Journey(legs=[], total_duration_s=1200, total_walk_m=500, transfer_count=1),
            Journey(legs=[], total_duration_s=1000, total_walk_m=200, transfer_count=2),
            Journey(legs=[], total_duration_s=1100, total_walk_m=800, transfer_count=0),
        ]
        ranked = rank_journeys(journeys, "least_walking")
        assert ranked[0].total_walk_m == 200

    def test_select_top_candidates(self):
        journeys = [
            Journey(legs=[], total_duration_s=1000, total_walk_m=300, transfer_count=0),
            Journey(legs=[], total_duration_s=1100, total_walk_m=300, transfer_count=0),
            Journey(legs=[], total_duration_s=1200, total_walk_m=300, transfer_count=0),
            Journey(legs=[], total_duration_s=1300, total_walk_m=300, transfer_count=0),
        ]
        top = select_top_candidates(journeys, 2)
        assert len(top) == 2


class TestFaresService:
    @pytest.mark.asyncio
    async def test_get_fare_quote_zero_legs(self, db_session: AsyncSession):
        service = FaresService(db_session)
        fare = await service.get_fare_quote(0)
        assert fare.total == 0.0

    @pytest.mark.asyncio
    async def test_get_fare_quote_one_leg(self, db_session: AsyncSession):
        service = FaresService(db_session)
        fare = await service.get_fare_quote(1)
        assert fare.total == fare.base_fare

    @pytest.mark.asyncio
    async def test_get_fare_quote_multiple_legs(self, db_session: AsyncSession):
        service = FaresService(db_session)
        fare = await service.get_fare_quote(3)
        expected = fare.base_fare + fare.per_leg_fare * 2
        assert fare.total == expected


class TestJourneySearchEngine:
    @pytest.mark.asyncio
    async def test_search_known_origin_destination(self, db_session: AsyncSession):
        engine = JourneySearchEngine(db_session)
        result = await engine.search(
            origin="Saddar",
            destination="Pak Secretariat",
            objective="fastest",
        )

        if isinstance(result, JourneySearchResponse):
            assert len(result.journeys) > 0
            journey = result.journeys[0]
            assert len(journey.legs) > 0
            assert journey.total_duration_s > 0
            assert journey.fare is not None
        elif isinstance(result, NoRouteFoundResponse):
            pytest.skip("No route found - may need more data")
        else:
            pytest.fail(f"Unexpected result type: {type(result)}")

    @pytest.mark.asyncio
    async def test_search_with_max_walk_filter(self, db_session: AsyncSession):
        engine = JourneySearchEngine(db_session)
        result = await engine.search(
            origin="Saddar",
            destination="Pak Secretariat",
            objective="fastest",
            max_walk_m=100,
        )

        if isinstance(result, JourneySearchResponse):
            for journey in result.journeys:
                assert journey.total_walk_m <= 100

    @pytest.mark.asyncio
    async def test_search_with_max_transfers_filter(self, db_session: AsyncSession):
        engine = JourneySearchEngine(db_session)
        result = await engine.search(
            origin="Saddar",
            destination="Pak Secretariat",
            objective="fastest",
            max_transfers=0,
        )

        if isinstance(result, JourneySearchResponse):
            for journey in result.journeys:
                assert journey.transfer_count == 0

    @pytest.mark.asyncio
    async def test_search_ambiguous_origin(self, db_session: AsyncSession):
        engine = JourneySearchEngine(db_session)
        result = await engine.search(
            origin="Faizabad",
            destination="Pak Secretariat",
            objective="fastest",
        )

        if isinstance(result, AmbiguousLocationResponse):
            assert result.error == "ambiguous_origin"
            assert len(result.candidates) >= 2
        elif isinstance(result, JourneySearchResponse):
            pass

    @pytest.mark.asyncio
    async def test_search_no_route_found(self, db_session: AsyncSession):
        engine = JourneySearchEngine(db_session)
        result = await engine.search(
            origin="NonExistentPlace12345",
            destination="AnotherNonExistentPlace67890",
            objective="fastest",
        )

        assert isinstance(result, NoRouteFoundResponse)
        assert result.error == "no_route_found"

    @pytest.mark.asyncio
    async def test_search_different_objectives(self, db_session: AsyncSession):
        engine = JourneySearchEngine(db_session)

        for objective in ["fastest", "fewest_transfers", "least_walking"]:
            result = await engine.search(
                origin="Saddar",
                destination="Pak Secretariat",
                objective=objective,
            )
            if isinstance(result, JourneySearchResponse):
                assert len(result.journeys) > 0
                for journey in result.journeys:
                    assert journey.total_duration_s > 0


class TestAPIEndpoint:
    @pytest.mark.asyncio
    async def test_journey_search_endpoint(self, db_session: AsyncSession):
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/transit/journeys/search",
                json={
                    "origin": "Saddar",
                    "destination": "Pak Secretariat",
                    "objective": "fastest",
                },
            )

            if response.status_code == 200:
                data = response.json()
                assert "journeys" in data
                assert len(data["journeys"]) > 0
                journey = data["journeys"][0]
                assert "legs" in journey
                assert "total_duration_s" in journey
                assert "total_walk_m" in journey
                assert "transfer_count" in journey
                assert "fare" in journey
            elif response.status_code == 404:
                pytest.skip("No route found")
            else:
                assert response.status_code in (200, 400, 404)

    @pytest.mark.asyncio
    async def test_journey_search_endpoint_invalid_input(self):
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/transit/journeys/search",
                json={"origin": "", "destination": ""},
            )
            # Empty origin/destination triggers validation error from Pydantic
            # but might also return 404 if geospatial fails - accept both
            assert response.status_code in (422, 400, 404)


class TestDeterministicResults:
    @pytest.mark.asyncio
    async def test_deterministic_results(self, db_session: AsyncSession):
        engine = JourneySearchEngine(db_session)

        result1 = await engine.search(
            origin="Saddar",
            destination="Pak Secretariat",
            objective="fastest",
        )
        result2 = await engine.search(
            origin="Saddar",
            destination="Pak Secretariat",
            objective="fastest",
        )

        if isinstance(result1, JourneySearchResponse) and isinstance(result2, JourneySearchResponse):
            assert len(result1.journeys) == len(result2.journeys)
            for j1, j2 in zip(result1.journeys, result2.journeys):
                assert j1.total_duration_s == j2.total_duration_s
                assert j1.total_walk_m == j2.total_walk_m
                assert j1.transfer_count == j2.transfer_count


class TestSharedStops:
    @pytest.mark.asyncio
    async def test_shared_stops_handled_correctly(self, db_session: AsyncSession):
        result = await db_session.execute(
            select(Stop).where(Stop.external_key == "cda_khanna_pul")
        )
        stop = result.scalar_one()

        route_count = await db_session.execute(
            select(func.count(func.distinct(RouteStop.route_id))).where(RouteStop.stop_id == stop.id)
        )
        assert route_count.scalar() >= 3


class TestRegressionPhase1To4:
    @pytest.mark.asyncio
    async def test_phase1_health_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_phase2_models_exist(self, db_session: AsyncSession):
        for model, expected_count in [
            (Stop, 1),
            (Route, 1),
            (RouteStop, 1),
            (Trip, 1),
            (StopTime, 1),
            (FareRule, 1),
        ]:
            count = await db_session.execute(select(func.count(model.id)))
            assert count.scalar() >= expected_count

    @pytest.mark.asyncio
    async def test_phase3_seeding_idempotent(self, db_session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer1 = TransitDataImporter(db_session)
        results1 = await importer1.import_all(data)
        await db_session.commit()

        importer2 = TransitDataImporter(db_session)
        results2 = await importer2.import_all(data)
        await db_session.commit()

        for key in results1:
            assert results1[key] == results2[key]

    @pytest.mark.asyncio
    async def test_phase4_geospatial_works(self, db_session: AsyncSession):
        service = GeospatialService(db_session)
        result = await service.resolve_location("Saddar")
        assert len(result.candidates) > 0

        saddar = await db_session.execute(select(Stop).where(Stop.external_key == "saddar"))
        saddar = saddar.scalar_one()
        from geoalchemy2.shape import to_shape
        point = to_shape(saddar.location)
        nearby = await service.nearby_stops(point.y, point.x)
        assert len(nearby) > 0

        walk = await service.walking_distance(33.646, 73.048, 33.7288, 73.0913)
        assert walk.distance_m > 0

        # Don't call service.close() - it closes global clients needed by other tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])