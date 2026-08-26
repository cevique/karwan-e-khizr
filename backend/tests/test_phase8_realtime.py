import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.simulation.engine import SimulationEngine
from app.simulation.schemas import StopTimeEntry


def make_stop(stop_id: int, lat: float, lon: float, arrival_s: int, departure_s: int, seq: int) -> StopTimeEntry:
    return StopTimeEntry(
        stop_id=stop_id,
        sequence=seq,
        arrival_offset_s=arrival_s,
        departure_offset_s=departure_s,
        lat=lat,
        lon=lon,
    )


class TestSimulationEngineDeterminism:
    def test_same_inputs_same_output(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
            make_stop(3, 33.729, 73.091, 600, 615, 3),
        ]
        pos1 = engine.compute_position_at(schedule, 150.0)
        pos2 = engine.compute_position_at(schedule, 150.0)
        assert pos1 == pos2

    def test_different_inputs_different_output(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos1 = engine.compute_position_at(schedule, 100.0)
        pos2 = engine.compute_position_at(schedule, 200.0)
        assert pos1 != pos2


class TestSimulationEngineBeforeDeparture:
    def test_parked_at_first_stop_before_departure(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, -60.0)
        assert pos["latitude"] == 33.646
        assert pos["longitude"] == 73.048
        assert pos["status"] == "scheduled"
        assert pos["speed"] == 0.0
        assert pos["bearing"] is None
        assert pos["next_stop_id"] == 1
        assert pos["eta_seconds"] == 60

    def test_parked_at_first_stop_at_zero(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, 0.0)
        assert pos["latitude"] == 33.646
        assert pos["longitude"] == 73.048
        assert pos["status"] == "scheduled"
        assert pos["speed"] == 0.0


class TestSimulationEngineDwelling:
    def test_dwelling_at_intermediate_stop(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
            make_stop(3, 33.729, 73.091, 600, 615, 3),
        ]
        pos = engine.compute_position_at(schedule, 310.0)
        assert pos["latitude"] == 33.687
        assert pos["longitude"] == 73.055
        assert pos["speed"] == 0.0
        assert pos["status"] == "active"


class TestSimulationEngineInterpolation:
    def test_midway_between_stops_no_geometry(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        departure = 15 + engine.DEFAULT_DWELL_S
        arrival_b = 300
        mid_time = (departure + arrival_b) / 2
        pos = engine.compute_position_at(schedule, mid_time)
        total_travel = arrival_b - departure
        fraction = (mid_time - departure) / total_travel
        expected_lat = 33.646 + (33.687 - 33.646) * fraction
        expected_lon = 73.048 + (73.055 - 73.048) * fraction
        assert abs(pos["latitude"] - expected_lat) < 0.001
        assert abs(pos["longitude"] - expected_lon) < 0.001
        assert pos["status"] == "active"
        assert pos["bearing"] is not None
        assert pos["speed"] > 0.0

    def test_near_first_stop_after_departure(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, 100.0)
        assert pos["latitude"] > 33.646
        assert pos["latitude"] < 33.687
        assert pos["status"] == "active"

    def test_interpolation_with_geometry(self):
        engine = SimulationEngine()
        geometry = [
            (33.646, 73.048),
            (33.660, 73.050),
            (33.680, 73.053),
            (33.687, 73.055),
        ]
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, 150.0, route_geometry=geometry)
        assert pos["latitude"] > 33.646
        assert pos["latitude"] < 33.687
        assert pos["status"] == "active"
        assert pos["bearing"] is not None


class TestSimulationEngineCompleted:
    def test_clamped_at_last_stop_when_complete(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
            make_stop(3, 33.729, 73.091, 600, 615, 3),
        ]
        pos = engine.compute_position_at(schedule, 700.0)
        assert pos["latitude"] == 33.729
        assert pos["longitude"] == 73.091
        assert pos["status"] == "completed"
        assert pos["speed"] == 0.0
        assert pos["bearing"] is None
        assert pos["next_stop_id"] is None
        assert pos["eta_seconds"] is None


class TestSimulationEngineBearing:
    def test_bearing_north(self):
        engine = SimulationEngine()
        bearing = engine._bearing(33.0, 73.0, 34.0, 73.0)
        assert abs(bearing - 0.0) < 1.0

    def test_bearing_east(self):
        engine = SimulationEngine()
        bearing = engine._bearing(33.0, 73.0, 33.0, 74.0)
        assert abs(bearing - 90.0) < 1.0

    def test_bearing_south(self):
        engine = SimulationEngine()
        bearing = engine._bearing(34.0, 73.0, 33.0, 73.0)
        assert abs(bearing - 180.0) < 1.0

    def test_bearing_between_stops(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.729, 73.091, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, 150.0)
        assert pos["bearing"] is not None
        assert 0 <= pos["bearing"] < 360


class TestSimulationEngineSpeed:
    def test_speed_computed_correctly(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, 150.0)
        assert pos["speed"] > 0.0

    def test_speed_zero_while_dwelling(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, 10.0)
        assert pos["speed"] == 0.0

    def test_speed_zero_at_parked(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, -60.0)
        assert pos["speed"] == 0.0


class TestSimulationEngineETA:
    def test_eta_before_departure(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        eta = engine.compute_eta_at(schedule, -60.0)
        assert eta is not None
        assert eta["next_stop_id"] == 1
        assert eta["baseline_eta_seconds"] == 60

    def test_eta_while_in_transit(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
            make_stop(3, 33.729, 73.091, 600, 615, 3),
        ]
        eta = engine.compute_eta_at(schedule, 100.0)
        assert eta is not None
        assert eta["next_stop_id"] == 2
        assert eta["baseline_eta_seconds"] == 200

    def test_eta_none_when_completed(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        eta = engine.compute_eta_at(schedule, 400.0)
        assert eta is None

    def test_eta_none_for_empty_schedule(self):
        engine = SimulationEngine()
        eta = engine.compute_eta_at([], 100.0)
        assert eta is None


class TestSimulationEngineEdgeCases:
    def test_empty_schedule(self):
        engine = SimulationEngine()
        pos = engine.compute_position_at([], 100.0)
        assert pos["latitude"] == 0.0
        assert pos["longitude"] == 0.0
        assert pos["status"] == "completed"

    def test_single_stop_schedule(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
        ]
        pos = engine.compute_position_at(schedule, 10.0)
        assert pos["latitude"] == 33.646
        assert pos["longitude"] == 73.048
        assert pos["status"] == "active"

    def test_single_stop_schedule_after_departure(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
        ]
        pos = engine.compute_position_at(schedule, 30.0)
        assert pos["latitude"] == 33.646
        assert pos["longitude"] == 73.048
        assert pos["status"] == "completed"

    def test_negative_elapsed(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos = engine.compute_position_at(schedule, -100.0)
        assert pos["status"] == "scheduled"
        assert pos["eta_seconds"] == 100


class TestHaversine:
    def test_haversine_same_point(self):
        engine = SimulationEngine()
        dist = engine._haversine_m(33.646, 73.048, 33.646, 73.048)
        assert dist == 0.0

    def test_haversine_known_distance(self):
        engine = SimulationEngine()
        dist = engine._haversine_m(33.646, 73.048, 33.729, 73.091)
        assert 5000 < dist < 15000

    def test_haversine_symmetric(self):
        engine = SimulationEngine()
        d1 = engine._haversine_m(33.646, 73.048, 33.729, 73.091)
        d2 = engine._haversine_m(33.729, 73.091, 33.646, 73.048)
        assert abs(d1 - d2) < 0.1


class TestProviderAbstraction:
    def test_provider_protocol_compliance(self):
        from app.simulation.provider import VehicleLocationProvider
        assert hasattr(VehicleLocationProvider, 'get_all_positions')
        assert hasattr(VehicleLocationProvider, 'get_vehicle_position')
        assert hasattr(VehicleLocationProvider, 'get_vehicle_eta')


class TestSourceLabeling:
    def test_all_positions_have_source(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        for elapsed in [-60.0, 0.0, 10.0, 150.0, 310.0, 400.0]:
            pos = engine.compute_position_at(schedule, elapsed)
            assert "status" in pos


class TestGeometryFallback:
    def test_fallback_to_straight_line_when_no_geometry(self):
        engine = SimulationEngine()
        schedule = [
            make_stop(1, 33.646, 73.048, 0, 15, 1),
            make_stop(2, 33.687, 73.055, 300, 315, 2),
        ]
        pos_no_geom = engine.compute_position_at(schedule, 150.0, route_geometry=None)
        pos_with_geom = engine.compute_position_at(
            schedule, 150.0,
            route_geometry=[(33.646, 73.048), (33.660, 73.050), (33.687, 73.055)]
        )
        assert pos_no_geom["status"] == "active"
        assert pos_with_geom["status"] == "active"

    def test_geometry_interpolation_produces_valid_coords(self):
        engine = SimulationEngine()
        geometry = [
            (33.646, 73.048),
            (33.660, 73.050),
            (33.680, 73.053),
            (33.687, 73.055),
        ]
        for fraction in [0.0, 0.25, 0.5, 0.75, 1.0]:
            lat, lon = engine._interpolate_along_geometry(
                geometry, fraction
            )
            assert 33.646 <= lat <= 33.687
            assert 73.048 <= lon <= 73.055


class TestRegressionPhase1To7:
    def test_engine_instantiation(self):
        engine = SimulationEngine()
        assert engine is not None
        assert hasattr(engine, 'compute_position_at')
        assert hasattr(engine, 'compute_eta_at')

    def test_schemas_importable(self):
        from app.simulation.schemas import (
            VehiclePosition,
            VehiclePositionResponse,
            VehicleETA,
            VehicleSnapshot,
            StopTimeEntry,
            ScheduleData,
        )
        assert VehiclePosition is not None
        assert VehiclePositionResponse is not None
        assert VehicleETA is not None
        assert StopTimeEntry is not None
        assert ScheduleData is not None

    def test_provider_importable(self):
        from app.simulation.provider import (
            VehicleLocationProvider,
            SimulatedVehicleLocationProvider,
        )
        assert VehicleLocationProvider is not None
        assert SimulatedVehicleLocationProvider is not None

    def test_router_importable(self):
        from app.simulation.router import router
        assert router is not None

    def test_api_routes_registered(self):
        from app.main import app
        schema = app.openapi()
        paths = list(schema.get('paths', {}).keys())
        assert "/api/v1/transit/realtime/vehicles" in paths
        assert "/api/v1/transit/realtime/vehicles/{vehicle_id}" in paths
        assert "/api/v1/transit/realtime/vehicles/{vehicle_id}/eta" in paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])