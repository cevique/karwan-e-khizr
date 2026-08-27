from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from app.eta.schemas import ETAFeatures
from app.simulation.schemas import StopTimeEntry


def extract_eta_features(
    stops: list[StopTimeEntry],
    current_elapsed_s: float,
    route_id: int,
    current_time: Optional[datetime] = None,
) -> Optional[ETAFeatures]:
    """Extract ETA prediction features from the current vehicle state.

    Given the current stop schedule and elapsed time, produces a feature
    vector suitable for the ETA predictor.

    Returns None if the vehicle state doesn't produce valid features
    (e.g. before departure, or past the last stop).
    """
    if not stops:
        return None

    if current_time is None:
        current_time = datetime.now(timezone.utc)

    last_stop = stops[-1]
    total_duration = last_stop.arrival_offset_s + 15  # DEFAULT_DWELL_S

    # Before departure
    if current_elapsed_s <= 0:
        return None

    # Past completion
    if current_elapsed_s >= total_duration:
        return None

    # Find next stop
    next_stop = None
    next_stop_idx = 0
    for i, stop in enumerate(stops):
        if current_elapsed_s < stop.arrival_offset_s:
            next_stop = stop
            next_stop_idx = i
            break

    if next_stop is None:
        return None

    # Find current stop (last stop whose arrival has passed)
    current_stop_idx = 0
    for i, stop in enumerate(stops):
        if current_elapsed_s >= stop.arrival_offset_s:
            current_stop_idx = i
        else:
            break

    # Scheduled duration remaining from current position to next stop
    scheduled_remaining = next_stop.arrival_offset_s - current_elapsed_s

    # Compute remaining distance to next stop
    current_stop = stops[current_stop_idx]
    distance_remaining = _haversine_m(
        current_stop.lat, current_stop.lon,
        next_stop.lat, next_stop.lon,
    )

    # Time-of-day and day-of-week features
    time_of_day = current_time.strftime("%H:%M")
    day_of_week = current_time.strftime("%A").lower()

    # Total scheduled duration for the trip
    scheduled_duration = total_duration

    return ETAFeatures(
        route_id=route_id,
        stop_id=next_stop.stop_id,
        time_of_day=time_of_day,
        day_of_week=day_of_week,
        scheduled_duration_s=scheduled_duration,
        distance_remaining_m=distance_remaining,
        delay_seconds=None,
    )


def extract_features_from_segments(
    stops: list[StopTimeEntry],
    route_id: int,
) -> list[ETAFeatures]:
    """Extract features for all stop-to-stop segments in a trip.

    Used during training data generation to create one observation
    per segment (current_stop → next_stop).
    """
    if len(stops) < 2:
        return []

    features = []
    for i in range(len(stops) - 1):
        current_stop = stops[i]
        next_stop = stops[i + 1]

        scheduled_remaining = next_stop.arrival_offset_s - current_stop.arrival_offset_s

        distance = _haversine_m(
            current_stop.lat, current_stop.lon,
            next_stop.lat, next_stop.lon,
        )

        features.append(ETAFeatures(
            route_id=route_id,
            stop_id=next_stop.stop_id,
            time_of_day="00:00",  # placeholder, filled by training generator
            day_of_week="monday",  # placeholder, filled by training generator
            scheduled_duration_s=scheduled_remaining,
            distance_remaining_m=distance,
            delay_seconds=None,
        ))

    return features


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two points."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
