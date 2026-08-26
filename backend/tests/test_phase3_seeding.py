import pytest
import json
from pathlib import Path
from collections import defaultdict
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


def _tier1_route_keys(data: dict) -> set[str]:
    return {r["key"] for r in data["routes"] if r.get("coverage_tier") == 1}


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
        assert len(data["trips"]) >= 4

    def test_all_22_cda_feeder_routes_present_and_classified(self):
        data = load_transit_data(TEST_DATA_PATH)
        feeder_keys = {
            r["key"] for r in data["routes"]
            if r["key"].startswith(("fr_", "frb_", "frg_", "st_"))
        }
        assert len(feeder_keys) == 22, f"expected 22 CDA feeder routes, found {len(feeder_keys)}: {sorted(feeder_keys)}"
        for r in data["routes"]:
            assert r.get("coverage_tier") in (1, 2, 3, 4), (
                f"route {r['key']} has no valid coverage_tier classification"
            )

    def test_route_stop_total_matches_per_route_breakdown(self):
        # Regression test for the "168 vs 145" discrepancy raised during
        # review: the total route_stops count must always equal the sum
        # of every individual route's own route_stops count - computed
        # here directly from the dataset, not hardcoded, so it can never
        # silently drift out of sync again. As of this pass: 9 Tier-1
        # feeder routes (mechanically derived from their canonical trip)
        # + Red Line's independently-sourced 23-stop sequence (Tier 2,
        # no canonical trip) = the total.
        data = load_transit_data(TEST_DATA_PATH)
        from collections import defaultdict
        per_route = defaultdict(int)
        for rs in data["route_stops"]:
            per_route[rs["route_id"]] += 1
        assert sum(per_route.values()) == len(data["route_stops"])

        route_key_by_id = {r["id"]: r["key"] for r in data["routes"]}
        tier1_route_ids = {
            t["route_id"] for t in data["trips"] if t.get("kind") == "CANONICAL_PATTERN"
        }
        tier1_total = sum(per_route[rid] for rid in tier1_route_ids)
        expected_tier1_total = sum(len(t["stop_times"]) for t in data["trips"] if t.get("kind") == "CANONICAL_PATTERN")
        assert tier1_total == expected_tier1_total, (
            f"Tier-1 route_stops total ({tier1_total}) must equal the sum of all "
            f"canonical trips' stop_times ({expected_tier1_total}) - they are "
            f"mechanically derived from each other and must never drift apart"
        )

        red_line_id = next(r["id"] for r in data["routes"] if r["key"] == "red_line")
        assert per_route[red_line_id] == 23

        # No route_stops exist for any route that is neither Tier 1 nor
        # Red Line (Tier 2) - Tier 3/4 routes have no verified topology.
        non_topology_route_ids = set(route_key_by_id) - tier1_route_ids - {red_line_id}
        for rid in non_topology_route_ids:
            assert per_route.get(rid, 0) == 0, (
                f"route {route_key_by_id[rid]} has route_stops but is not Tier 1 or "
                f"Red Line - unexpected topology for an unverified route"
            )

    def test_no_dead_top_level_stop_times_key(self):
        # Schema audit finding: an earlier draft of this dataset carried
        # an always-empty, never-populated, never-read top-level
        # "stop_times" key (the importer only ever reads
        # trips[].stop_times). Removed as a vestigial artifact - this is
        # a regression test to make sure it doesn't silently reappear.
        data = load_transit_data(TEST_DATA_PATH)
        assert "stop_times" not in data

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
        data = load_transit_data(TEST_DATA_PATH)
        assert imported_data["routes"] == len(data["routes"])

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
    async def test_all_22_feeder_routes_imported(self, session: AsyncSession, imported_data):
        data = load_transit_data(TEST_DATA_PATH)
        feeder_short_names = [
            r["short_name"] for r in data["routes"]
            if r["key"].startswith(("fr_", "frb_", "frg_", "st_"))
        ]
        assert len(feeder_short_names) == 22

        result = await session.execute(
            select(func.count(Route.id)).where(Route.route_type == "feeder")
        )
        assert result.scalar() == 22

        for short_name in feeder_short_names:
            result = await session.execute(select(Route).where(Route.short_name == short_name))
            route = result.scalar_one()
            assert route.route_type == "feeder"

    @pytest.mark.asyncio
    async def test_stops_imported_correctly(self, session: AsyncSession, imported_data):
        assert imported_data["stops"] > 0

        result = await session.execute(select(func.count(Stop.id)))
        count = result.scalar()
        assert count == imported_data["stops"]

        result = await session.execute(select(Stop).where(Stop.external_key == "saddar"))
        saddar = result.scalar_one()
        assert saddar.name == "Saddar"
        assert saddar.location is not None
        assert saddar.coordinate_source == "curated"
        assert saddar.coordinate_confidence == "APPROXIMATE"

    @pytest.mark.asyncio
    async def test_stop_display_name_is_not_the_slug(self, session: AsyncSession, imported_data):
        data = load_transit_data(TEST_DATA_PATH)
        for stop_data in data["stops"]:
            result = await session.execute(
                select(Stop).where(Stop.external_key == stop_data["key"])
            )
            stop = result.scalar_one()
            assert stop.name == stop_data["name"], (
                f"stop {stop_data['key']}: DB name {stop.name!r} does not match "
                f"dataset name {stop_data['name']!r} - looks like the slug leaked "
                f"into the display name again"
            )
            if stop_data["key"] != stop_data["name"]:
                assert stop.name != stop_data["key"]

    @pytest.mark.asyncio
    async def test_route_stop_sequences_preserved(self, session: AsyncSession, imported_data):
        assert imported_data["route_stops"] > 0

        result = await session.execute(select(func.count(RouteStop.id)))
        count = result.scalar()
        assert count == imported_data["route_stops"]

        result = await session.execute(
            select(RouteStop, Stop.external_key, Route.short_name)
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
    async def test_no_duplicate_route_stop_sequences(self, session: AsyncSession, imported_data):
        result = await session.execute(select(RouteStop.route_id, RouteStop.sequence))
        pairs = result.all()
        assert len(pairs) == len(set(pairs)), "duplicate (route_id, sequence) pairs found in route_stops"

    @pytest.mark.asyncio
    async def test_tier1_routes_have_route_stops_matching_their_canonical_trip(
        self, session: AsyncSession, imported_data
    ):
        data = load_transit_data(TEST_DATA_PATH)
        stop_uuid_to_key = {s["id"]: s["key"] for s in data["stops"]}

        for trip_data in data["trips"]:
            if trip_data.get("kind") != "CANONICAL_PATTERN":
                continue
            route_id_uuid = trip_data["route_id"]
            route_key = next(
                r["key"] for r in data["routes"] if r["id"] == route_id_uuid
            )
            short_name = next(r["short_name"] for r in data["routes"] if r["key"] == route_key)

            expected_keys = [stop_uuid_to_key[st["stop_id"]] for st in trip_data["stop_times"]]

            result = await session.execute(
                select(Stop.external_key)
                .join(RouteStop, RouteStop.stop_id == Stop.id)
                .join(Route, RouteStop.route_id == Route.id)
                .where(Route.short_name == short_name)
                .order_by(RouteStop.sequence)
            )
            actual_keys = [row[0] for row in result.all()]
            assert actual_keys == expected_keys, f"{short_name}: RouteStop order doesn't match its canonical trip"

    @pytest.mark.asyncio
    async def test_trips_imported_correctly(self, session: AsyncSession, imported_data):
        data = load_transit_data(TEST_DATA_PATH)
        expected_trip_count = len(data["trips"])
        assert imported_data["trips"] == expected_trip_count

        result = await session.execute(select(func.count(Trip.id)))
        count = result.scalar()
        assert count == expected_trip_count

        result = await session.execute(
            select(Trip, Route.short_name)
            .join(Route, Trip.route_id == Route.id)
            .order_by(Route.short_name, Trip.direction_id)
        )
        trips = result.all()
        route_names = {t[1] for t in trips}
        for expected in ("FR-01", "FR-03A", "FR-04", "FR-06", "FR-07", "FR-09", "FR-10", "FR-14", "FR-15"):
            assert expected in route_names

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
        data = load_transit_data(TEST_DATA_PATH)
        expected_count = len(data.get("fare_rules", []))
        assert imported_data["fare_rules"] == expected_count

        result = await session.execute(select(func.count(FareRule.id)))
        count = result.scalar()
        assert count == expected_count

        result = await session.execute(select(FareRule).where(FareRule.name == "Standard Metrobus"))
        metrobus = result.scalar_one()
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

        result = await session.execute(select(func.count(RouteStop.id)))
        assert result.scalar() == results1["route_stops"]


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
            select(Stop).where(Stop.external_key.in_(faizabad_stops))
        )
        stops = result.scalars().all()
        assert len(stops) == len(faizabad_stops)

        result = await session.execute(select(func.count(Stop.id)).where(Stop.external_key.in_(faizabad_stops)))
        assert result.scalar() == len(faizabad_stops)

    @pytest.mark.asyncio
    async def test_duplicate_keys_in_source_do_not_create_duplicate_rows(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        keys = [s["key"] for s in data["stops"]]
        assert len(keys) == len(set(keys)), "duplicate stop keys found in transit_data.json"

        importer = TransitDataImporter(session)
        results = await importer.import_all(data)
        await session.commit()

        result = await session.execute(select(func.count(Stop.id)))
        assert result.scalar() == len(set(keys)) == results["stops"]


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
        expected_located = sum(1 for s in data["stops"] if s.get("latitude") is not None)

        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(Stop).where(Stop.location.is_not(None))
        )
        located = result.scalars().all()
        assert len(located) == expected_located

        for stop in located:
            assert stop.coordinate_source is not None
            assert stop.coordinate_confidence is not None
            assert stop.coordinate_confidence in ("HIGH", "APPROXIMATE")

    @pytest.mark.asyncio
    async def test_unknown_stops_remain_without_coordinates(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        expected_unknown = sum(1 for s in data["stops"] if s.get("latitude") is None)

        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(Stop).where(Stop.location.is_(None))
        )
        unknown = result.scalars().all()
        assert len(unknown) == expected_unknown

        for stop in unknown:
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
            from geoalchemy2.shape import to_shape
            point = to_shape(stop.location)
            assert point.geom_type == "Point"
            lat, lon = point.y, point.x
            assert 33.0 <= lat <= 34.5
            assert 72.5 <= lon <= 73.5

    @pytest.mark.asyncio
    async def test_newly_added_cda_pdf_stops_have_no_coordinates(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        cda_pdf_keys = [
            s["key"] for s in data["stops"]
            if s["key"].startswith("cda_") and s.get("latitude") is None
        ]
        assert len(cda_pdf_keys) > 0

        result = await session.execute(
            select(Stop).where(Stop.external_key.in_(cda_pdf_keys))
        )
        stops = result.scalars().all()
        assert len(stops) == len(cda_pdf_keys)
        for stop in stops:
            assert stop.location is None


class TestTimetables:
    @pytest.fixture
    async def session(self):
        await init_db()
        async with AsyncSessionLocal() as session:
            yield session
        await close_db()

    async def _assert_timetable(self, session, short_name, first_key, last_key):
        result = await session.execute(
            select(StopTime, Stop.external_key)
            .join(Stop, StopTime.stop_id == Stop.id)
            .join(Trip, StopTime.trip_id == Trip.id)
            .join(Route, Trip.route_id == Route.id)
            .where(Route.short_name == short_name)
            .order_by(StopTime.sequence)
        )
        rows = result.all()
        assert len(rows) > 0
        assert rows[0][1] == first_key
        assert rows[0][0].arrival_offset_s == 0
        assert rows[0][0].departure_offset_s == 0
        assert rows[-1][1] == last_key

    @pytest.mark.asyncio
    async def test_fr01_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(StopTime, Stop.external_key)
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
        await self._assert_timetable(session, "FR-04", "cda_pims_hospital", "cda_bari_imam")

    @pytest.mark.asyncio
    async def test_fr06_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()
        await self._assert_timetable(session, "FR-06", "cda_pims_metro_station", "cda_golra_sharif")

    @pytest.mark.asyncio
    async def test_fr07_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(StopTime, Stop.external_key)
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
    async def test_fr09_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()
        await self._assert_timetable(session, "FR-09", "cda_khanna_pul", "cda_golra_morh_metro_station")

    @pytest.mark.asyncio
    async def test_fr14_timetable_data(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        result = await session.execute(
            select(StopTime, Stop.external_key)
            .join(Stop, StopTime.stop_id == Stop.id)
            .join(Trip, StopTime.trip_id == Trip.id)
            .join(Route, Trip.route_id == Route.id)
            .where(Route.short_name == "FR-14")
            .order_by(StopTime.sequence)
        )
        fr14_times = result.all()

        assert len(fr14_times) > 15
        assert fr14_times[0][1] == "cda_barakahu"

    @pytest.mark.asyncio
    async def test_fr03a_timetable_data(self, session: AsyncSession):
        # New this correction pass: PIMS Hospital -> Flower Market, 13
        # stops, 97 trips/day, 10-min headway. Long Name on the source
        # PDF itself ("PIMS Hospital to Faisal Masjid") does not match
        # the route's actual last stop (Flower Market) - see
        # docs/DATA_GAPS.md for this preserved conflict.
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()
        await self._assert_timetable(session, "FR-03A", "cda_pims_hospital", "cda_flower_market")

    @pytest.mark.asyncio
    async def test_fr10_timetable_data(self, session: AsyncSession):
        # New this correction pass: Golra Morh -> Taxila, 25 stops,
        # 19 trips/day, printed average headway 50 min (actual gaps
        # alternate 30/60 min - preserved as printed, not corrected).
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()
        await self._assert_timetable(session, "FR-10", "cda_golra_morh", "cda_taxila")

    @pytest.mark.asyncio
    async def test_fr15_timetable_data(self, session: AsyncSession):
        # New this correction pass: Khanna Pul -> T-Chowk, 16 stops,
        # 33 trips/day, 30-min headway.
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()
        await self._assert_timetable(session, "FR-15", "cda_khanna_pul", "cda_t_chowk")

    @pytest.mark.asyncio
    async def test_shared_stops_are_a_single_row_across_routes(self, session: AsyncSession):
        # Real-world corridor overlap: e.g. "Khanna Pul" is the start of
        # FR-01, FR-09, and FR-15; "NUST Metro Station" appears on FR-01,
        # FR-07, and FR-10. These must resolve to ONE Stop row each, not
        # a duplicate per route.
        data = load_transit_data(TEST_DATA_PATH)
        importer = TransitDataImporter(session)
        await importer.import_all(data)
        await session.commit()

        for key, expected_min_routes in [("cda_khanna_pul", 3), ("cda_nust_metro_station", 3)]:
            result = await session.execute(select(Stop).where(Stop.external_key == key))
            stops = result.scalars().all()
            assert len(stops) == 1, f"{key} should resolve to exactly one Stop row, found {len(stops)}"

            route_count = await session.execute(
                select(func.count(func.distinct(RouteStop.route_id))).where(RouteStop.stop_id == stops[0].id)
            )
            assert route_count.scalar() >= expected_min_routes

    @pytest.mark.asyncio
    async def test_no_route_has_more_than_one_canonical_trip_per_direction(self, session: AsyncSession):
        data = load_transit_data(TEST_DATA_PATH)
        seen = defaultdict(int)
        for t in data["trips"]:
            if t.get("kind") != "CANONICAL_PATTERN":
                continue
            seen[(t["route_id"], t.get("direction"))] += 1
        for key, n in seen.items():
            assert n == 1, f"route/direction {key} has {n} canonical trip patterns, expected 1"


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
        expected_names = {fr["name"] for fr in data["fare_rules"]}
        assert set(rule_names) == expected_names

        for fr_data in data["fare_rules"]:
            db_rule = rule_names[fr_data["name"]]
            assert db_rule.base_fare == fr_data["base_fare"]
            assert db_rule.per_leg_fare == fr_data["per_leg_fare"]
            assert db_rule.currency == fr_data.get("currency", "PKR")

    @pytest.mark.asyncio
    async def test_fare_rules_carry_provenance_in_source_dataset(self):
        data = load_transit_data(TEST_DATA_PATH)
        for fr in data["fare_rules"]:
            assert "source" in fr and fr["source"]
            assert fr.get("confidence") == "APPROXIMATE"


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
        assert results["trips"] == len(data["trips"])
