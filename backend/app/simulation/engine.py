from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from app.simulation.schemas import StopTimeEntry


class SimulationEngine:
    """Pure, deterministic simulation — same inputs always produce same output.

    Given an ordered stop schedule and elapsed seconds, returns exactly one
    vehicle position with bearing and speed. No side effects.
    """

    DEFAULT_DWELL_S: int = 15
    DEFAULT_SPEED_MPS: float = 13.9

    def compute_position_at(
        self,
        schedule: list[StopTimeEntry],
        elapsed_s: float,
        route_geometry: Optional[list[tuple[float, float]]] = None,
        current_time: datetime | None = None,
    ) -> dict:
        if not schedule:
            return {
                "latitude": 0.0,
                "longitude": 0.0,
                "bearing": None,
                "speed": 0.0,
                "status": "completed",
                "next_stop_id": None,
                "eta_seconds": None,
            }

        if elapsed_s <= 0:
            first_stop = schedule[0]
            return {
                "latitude": first_stop.lat,
                "longitude": first_stop.lon,
                "bearing": None,
                "speed": 0.0,
                "status": "scheduled",
                "next_stop_id": first_stop.stop_id,
                "eta_seconds": max(0, int(-elapsed_s)),
            }

        if len(schedule) == 1:
            stop = schedule[0]
            departure_end = stop.departure_offset_s + self.DEFAULT_DWELL_S
            if elapsed_s >= departure_end:
                return {
                    "latitude": stop.lat,
                    "longitude": stop.lon,
                    "bearing": None,
                    "speed": 0.0,
                    "status": "completed",
                    "next_stop_id": None,
                    "eta_seconds": None,
                }
            else:
                return {
                    "latitude": stop.lat,
                    "longitude": stop.lon,
                    "bearing": None,
                    "speed": 0.0,
                    "status": "active",
                    "next_stop_id": None,
                    "eta_seconds": None,
                }

        last_stop = schedule[-1]
        total_duration = last_stop.arrival_offset_s + self.DEFAULT_DWELL_S
        if elapsed_s >= total_duration:
            return {
                "latitude": last_stop.lat,
                "longitude": last_stop.lon,
                "bearing": None,
                "speed": 0.0,
                "status": "completed",
                "next_stop_id": None,
                "eta_seconds": None,
            }

        current_stop_idx = 0
        for i in range(len(schedule)):
            if elapsed_s >= schedule[i].arrival_offset_s:
                current_stop_idx = i
            else:
                break

        if current_stop_idx >= len(schedule) - 1:
            current_stop = schedule[current_stop_idx]
            departure_end = current_stop.departure_offset_s + self.DEFAULT_DWELL_S
            if elapsed_s >= departure_end:
                return {
                    "latitude": current_stop.lat,
                    "longitude": current_stop.lon,
                    "bearing": None,
                    "speed": 0.0,
                    "status": "completed",
                    "next_stop_id": None,
                    "eta_seconds": None,
                }
            else:
                return {
                    "latitude": current_stop.lat,
                    "longitude": current_stop.lon,
                    "bearing": None,
                    "speed": 0.0,
                    "status": "active",
                    "next_stop_id": None,
                    "eta_seconds": None,
                }

        stop_a = schedule[current_stop_idx]
        stop_b = schedule[current_stop_idx + 1]

        departure_time = stop_a.departure_offset_s + self.DEFAULT_DWELL_S
        is_dwelling = elapsed_s < departure_time

        if is_dwelling:
            lat = stop_a.lat
            lon = stop_a.lon
            speed = 0.0
            bearing = None
        else:
            travel_time_in_segment = elapsed_s - departure_time
            arrival_time_b = stop_b.arrival_offset_s
            total_travel_time = float(arrival_time_b - departure_time)
            if total_travel_time <= 0:
                fraction = 1.0
            else:
                fraction = min(1.0, travel_time_in_segment / total_travel_time)

            if route_geometry and len(route_geometry) >= 2:
                lat, lon = self._interpolate_along_geometry(
                    route_geometry, fraction
                )
            else:
                lat = stop_a.lat + (stop_b.lat - stop_a.lat) * fraction
                lon = stop_a.lon + (stop_b.lon - stop_a.lon) * fraction

            seg_distance = self._haversine_m(stop_a.lat, stop_a.lon, stop_b.lat, stop_b.lon)
            speed = seg_distance / total_travel_time if total_travel_time > 0 else 0.0
            bearing = self._bearing(stop_a.lat, stop_a.lon, stop_b.lat, stop_b.lon)

        next_stop = stop_b
        time_to_next = stop_b.arrival_offset_s - elapsed_s

        next_stop_id = next_stop.stop_id if next_stop is not None else None
        eta = max(0, int(time_to_next)) if time_to_next is not None else None

        return {
            "latitude": lat,
            "longitude": lon,
            "bearing": bearing,
            "speed": speed,
            "status": "active",
            "next_stop_id": next_stop_id,
            "eta_seconds": eta,
        }

    def compute_eta_at(
        self,
        schedule: list[StopTimeEntry],
        elapsed_s: float,
    ) -> Optional[dict]:
        if not schedule:
            return None

        if elapsed_s <= 0:
            return {
                "next_stop_id": schedule[0].stop_id,
                "baseline_eta_seconds": max(0, int(-elapsed_s)),
            }

        if len(schedule) == 1:
            stop = schedule[0]
            departure_end = stop.departure_offset_s + self.DEFAULT_DWELL_S
            if elapsed_s >= departure_end:
                return None
            return {
                "next_stop_id": stop.stop_id,
                "baseline_eta_seconds": 0,
            }

        last_stop = schedule[-1]
        total_duration = last_stop.arrival_offset_s + self.DEFAULT_DWELL_S
        if elapsed_s >= total_duration:
            return None

        next_stop_idx = 0
        for i in range(len(schedule)):
            if elapsed_s < schedule[i].arrival_offset_s:
                next_stop_idx = i
                break
        else:
            next_stop_idx = len(schedule) - 1

        next_stop = schedule[next_stop_idx]
        eta = max(0, int(next_stop.arrival_offset_s - elapsed_s))

        return {
            "next_stop_id": next_stop.stop_id,
            "baseline_eta_seconds": eta,
        }

    def _interpolate_along_geometry(
        self,
        geometry: list[tuple[float, float]],
        fraction: float,
    ) -> tuple[float, float]:
        if len(geometry) < 2:
            return geometry[0] if geometry else (0.0, 0.0)

        total_geom_length = 0.0
        segments: list[float] = []
        for i in range(len(geometry) - 1):
            seg_len = self._haversine_m(
                geometry[i][0], geometry[i][1],
                geometry[i + 1][0], geometry[i + 1][1],
            )
            segments.append(seg_len)
            total_geom_length += seg_len

        if total_geom_length == 0:
            return geometry[0]

        target_distance = total_geom_length * fraction

        cumulative = 0.0
        for i, seg_len in enumerate(segments):
            if cumulative + seg_len >= target_distance:
                if seg_len == 0:
                    return geometry[i]
                local_fraction = (target_distance - cumulative) / seg_len
                lat = geometry[i][0] + (geometry[i + 1][0] - geometry[i][0]) * local_fraction
                lon = geometry[i][1] + (geometry[i + 1][1] - geometry[i][1]) * local_fraction
                return lat, lon
            cumulative += seg_len

        return geometry[-1]

    @staticmethod
    def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dlam = math.radians(lon2 - lon1)
        x = math.sin(dlam) * math.cos(phi2)
        y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360