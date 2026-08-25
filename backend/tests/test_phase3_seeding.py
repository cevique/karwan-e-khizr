import pytest
import json
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_db, close_db, AsyncSessionLocal
from app.seeding.importer import TransitDataImporter, load_transit_data
from app.db.models.agency import Agency
from app.db.models.route import Route
from app.db.models.stop import Stop
from app.db.models.route_stop import RouteStop
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.db.models.fare_rule import FareRule


TEST_DATA_PATH = Path("data/transit_data.json")


class TestDatasetParsing:
    def test_canonical_json_loads_successfully(self):
        data = load_transit_data(TEST_DATA_PATH)
        assert data is not None
        assert isinstance(data, dict)

    def test_expected_top_level_structure_exists(self):
        data = load_transit_data(TEST_DATA_PATH)
        required_sections = [
            "operators", "stops", "routes", "route_stops",
            "trips", "service_calendars", "transfers"
        ]
        for section in required_sections:
            assert section in data, f"Missing required section: {section}"

    def test_required_sections_exist(self):
        data = load_transit_data(TEST_DATA_PATH)
        assert len(data["operators"]) == 2
        assert len(data["stops"]) > 0
        assert len(data["routes"]) > 0
        assert len(data["route_stops"]) > 0
        assert len(data["trips"]) == 4

    def test_malformed_records_fail(self, tmp_path):
        invalid_file = tmp_path / "test_invalid.json"
        invalid_file.write_text("{ invalid json }")
        with pytest.raises(json.JSONDecodeError):
            load_transit_data(invalid_file)


class TestDatabaseImport:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    @pytest.fixture
    async def imported_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        results = await importer.import_all(data)
        await session.commit()
        return results

    @pytest.mark.asyncio
    async def test_agencies_imported_correctly(self, session: AsyncSession, imported_data):
        assert imported_data["agencies"] == 2

        result = await session.execute(select(func.count(Agency.id)))
        count = result.scalar()
        assert count == 2

        result = await session.execute(select(Agency).where(Agency.short_name == "pmta"))
        pmta = result.scalar_one()
        assert pmta.name == "Punjab Mass Transit Authority (PMTA)"
        assert pmta.timezone == "Asia/Karachi"

        result = await session.execute(select(Agency).where(Agency.short_name == "cda_cmta"))
        cda = result.scalar_one()
        assert cda.name == "Capital Development Authority (CDA) / Capital Mass Transit Authority (CMTA)"

    @pytest.mark.asyncio
    async def test_routes_imported_correctly(self, session: AsyncSession, imported_data):
        assert imported_data["routes"] > 0

        result = await session.execute(select(func.count(Route.id)))
        count = result.scalar()
        assert count == imported_data["routes"]

        result = await session.execute(select(Route).where(Route.short_name == "Red"))
        red = result.scalar_one()
        assert red.route_type == "metro"
        assert red.color == "#C62828"

        result = await session.execute(select(Agency).where(Agency.short_name == "pmta"))
        pmta = result.scalar_one()
        assert red.agency_id == pmta.id

        result = await session.execute(select(Route).where(Route.short_name == "FR-01"))
        fr01 = result.scalar_one()
        assert fr01.route_type == "feeder"

    @pytest.mark.asyncio
    async def test_stops_imported_correctly(self, session: AsyncSession, imported_data):
        assert imported_data["stops"] > 0

        result = await session.execute(select(func.count(Stop.id)))
        count = result.scalar()
        assert count == imported_data["stops"]

        result = await session.execute(select(Stop).where(Stop.name == "saddar"))
        saddar = result.scalar_one()
        assert saddar.location is not None
        assert saddar.coordinate_source == "curated"
        assert saddar.coordinate_confidence == "APPROXIMATE"

    @pytest.mark.asyncio
    async def test_route_stop_sequences_preserved(self, session: AsyncSession, imported_data):
        assert imported_data["route_stops"] > 0

        result = await session.execute(select(func.count(RouteStop.id)))
        count = result.scalar()
        assert count == imported_data["route_stops"]

        result = await session.execute(
            select(RouteStop, Stop.name, Route.short_name)
            .join(Stop, RouteStop.stop_id == Stop.id)
            .join(Route, RouteStop.route_id == Route.id)
            .where(Route.short_name == "Red")
            .order_by(RouteStop.sequence)
        )
        red_stops = result.all()
        assert len(red_stops) == 23
        assert red_stops[0][1] == "saddar"
        assert red_stops[-1][1] == "pak_secretariat"

    @pytest.mark.asyncio
    async def test_trips_imported_correctly(self, session: AsyncSession, imported_data):
        assert imported_data["trips"] == 4

        result = await session.execute(select(func.count(Trip.id)))
        count = result.scalar()
        assert count == 4

        result = await session.execute(
            select(Trip, Route.short_name)
            .join(Route, Trip.route_id == Route.id)
            .order_by(Route.short_name, Trip.direction_id)
        )
        trips = result.all()
        route_names = [t[1] for t in trips]
        assert "FR-01" in route_names
        assert "FR-04" in route_names
        assert "FR-07" in route_names
        assert "FR-14" in route_names

    @pytest.mark.asyncio
    async def test_stop_times_imported_correctly(self, session: AsyncSession, imported_data):
        assert imported_data["stop_times"] > 0

        result = await session.execute(select(func.count(StopTime.id)))
        count = result.scalar()
        assert count == imported_data["stop_times"]

        result = await session.execute(
            select(StopTime)
            .join(Trip, StopTime.trip_id == Trip.id)
            .join(Route, Trip.route_id == Route.id)
            .where(Route.short_name == "FR-01")
            .order_by(StopTime.sequence)
        )
        fr01_stop_times = result.scalars().all()
        assert len(fr01_stop_times) > 0
        assert fr01_stop_times[0].arrival_offset_s == 0
        assert fr01_stop_times[0].departure_offset_s == 0

    @pytest.mark.asyncio
    async def test_fare_rules_imported_correctly(self, session: AsyncSession, imported_data):
        assert imported_data["fare_rules"] == 2

        result = await session.execute(select(func.count(FareRule.id)))
        count = result.scalar()
        assert count == 2

        result = await session.execute(select(FareRule).where(FareRule.name == "Standard Metrobus"))
        metrobus = result.scalar_one()
        assert metrobus.base_fare == 50.0
        assert metrobus.per_leg_fare == 20.0
        assert metrobus.currency == "PKR"
        assert metrobus.is_active is True


class TestIdempotency:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    @pytest.mark.asyncio
    async def test_import_twice_is_idempotent(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)

        importer1 = TransitDataImporter(session)
        results1 = await importer1.import_all(data)
        await session.commit()

        importer2 = TransitDataImporter(session)
        results2 = await importer2.import_all(data)
        await session.commit()

        for key in results1:
            assert results1[key] == results2[key], f"Count mismatch for {key}: {results1[key]} vs {results2[key]}"

        result = await session.execute(select(func.count(Agency.id)))
        assert result.scalar() == 2

        result = await session.execute(select(func.count(Route.id)))
        assert result.scalar() == results1["routes"]

        result = await session.execute(select(func.count(Stop.id)))
        assert result.scalar() == results1["stops"]


class TestStopCollisions:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    @pytest.mark.asyncio
    async def test_distinct_stops_with_same_name_remain_distinct(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        faizabad_stops = []
        for stop_data in data["stops"]:
            if "faizabad" in stop_data["key"].lower() or "faiz_ahmed_faiz" in stop_data["key"].lower():
                faizabad_stops.append(stop_data["key"])

        assert len(faizabad_stops) >= 2

        result = await session.execute(
            select(Stop).where(Stop.name.in_(faizabad_stops))
        )
        stops = result.scalars().all()
        assert len(stops) == len(faizabad_stops)

        result = await session.execute(select(func.count(Stop.id)).where(Stop.name.in_(faizabad_stops)))
        assert result.scalar() == len(faizabad_stops)


class TestCoordinates:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    @pytest.mark.asyncio
    async def test_located_stops_have_coordinates(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(Stop).where(Stop.location.is_not(None))
        )
        located = result.scalars().all()
        # Canonical data has 17 stops with coordinates
        assert len(located) == 17

        for stop in located:
            assert stop.coordinate_source is not None
            assert stop.coordinate_confidence is not None
            assert stop.coordinate_confidence in ("HIGH", "APPROXIMATE")

    @pytest.mark.asyncio
    async def test_unknown_stops_remain_without_coordinates(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(Stop).where(Stop.location.is_(None))
        )
        unknown = result.scalars().all()
        # Canonical data has 105 stops without coordinates
        assert len(unknown) == 105

        for stop in unknown:
            # Stops without coords can have various coordinate_source/confidence
            assert stop.coordinate_source is not None
            assert stop.coordinate_confidence is not None

    @pytest.mark.asyncio
    async def test_no_fabricated_coordinates(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(Stop).where(Stop.location.is_not(None))
        )
        located = result.scalars().all()

        for stop in located:
            # PostGIS returns EWKB binary, check it's valid
            from geoalchemy2.shape import to_shape
            point = to_shape(stop.location)
            assert point.geom_type == "Point"
            lat, lon = point.y, point.x
            assert 33.0 <= lat <= 34.5
            assert 72.5 <= lon <= 73.5


class TestTimetables:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    @pytest.mark.asyncio
    async def test_fr01_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(StopTime, Stop.name)
            .join(Stop, StopTime.stop_id == Stop.id)
            .join(Trip, StopTime.trip_id == Trip.id)
            .join(Route, Trip.route_id == Route.id)
            .where(Route.short_name == "FR-01")
            .order_by(StopTime.sequence)
        )
        fr01_times = result.all()

        assert len(fr01_times) > 20
        assert fr01_times[0][1] == "cda_khanna_pul"
        assert fr01_times[0][0].arrival_offset_s == 0
        assert fr01_times[0][0].departure_offset_s == 0

        last = fr01_times[-1]
        assert last[1] == "cda_nust_metro_station"
        assert last[0].arrival_offset_s == 3493
        assert last[0].departure_offset_s == 3493

    @pytest.mark.asyncio
    async def test_fr04_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(StopTime, Stop.name)
            .join(Stop, StopTime.stop_id == Stop.id)
            .join(Trip, StopTime.trip_id == Trip.id)
            .join(Route, Trip.route_id == Route.id)
            .where(Route.short_name == "FR-04")
            .order_by(StopTime.sequence)
        )
        fr04_times = result.all()

        assert len(fr04_times) > 20
        assert fr04_times[0][1] == "cda_pims_hospital"
        assert fr04_times[-1][1] == "cda_bari_imam"

    @pytest.mark.asyncio
    async def test_fr07_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(StopTime, Stop.name)
            .join(Stop, StopTime.stop_id == Stop.id)
            .join(Trip, StopTime.trip_id == Trip.id)
            .join(Route, Trip.route_id == Route.id)
            .where(Route.short_name == "FR-07")
            .order_by(StopTime.sequence)
        )
        fr07_times = result.all()

        assert len(fr07_times) > 20
        assert fr07_times[0][1] == "cda_pims_hospital"

    @pytest.mark.asyncio
    async def test_fr14_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(StopTime, Stop.name)
            .join(Stop, StopTime.stop_id == Stop.id)
            .join(Trip, StopTime.trip_id == Trip.id)
            .join(Route, Trip.route_id == Route.id)
            .where(Route.short_name == "FR-14")
            .order_by(StopTime.sequence)
        )
        fr14_times = result.all()

        assert len(fr14_times) > 15
        assert fr14_times[0][1] == "cda_barakahu"


class TestFareRules:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    @pytest.mark.asyncio
    async def test_fare_rules_match_canonical_dataset(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(select(FareRule))
        rules = result.scalars().all()

        rule_names = {r.name: r for r in rules}
        assert "Standard Metrobus" in rule_names
        assert "Feeder Route" in rule_names

        metrobus = rule_names["Standard Metrobus"]
        assert metrobus.base_fare == 50.0
        assert metrobus.per_leg_fare == 20.0

        feeder = rule_names["Feeder Route"]
        assert feeder.base_fare == 30.0
        assert feeder.per_leg_fare == 15.0


class TestEmptyOptionalFields:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    @pytest.mark.asyncio
    async def test_import_with_empty_optional_fields_succeeds(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        results = await importer.import_all(data)
        await session.commit()

        assert results["stops"] > 0
        assert results["routes"] > 0
        assert results["trips"] == 4