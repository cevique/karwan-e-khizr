from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

from app.eta.schemas import TrainingSample
from app.simulation.engine import SimulationEngine
from app.simulation.schemas import StopTimeEntry

logger = structlog.get_logger(__name__)

# Default output directory for synthetic training data
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "eta_training"

# Synthetic training data is explicitly labeled — it is NOT authoritative transit data.
SYNTHETIC_SOURCE = "synthetic"

# Number of different time-of-day samples to generate per trip
TIME_SAMPLES_PER_TRIP = 12

# Day-of-week options
DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def generate_synthetic_dataset(
    schedules: list[dict],
    engine: Optional[SimulationEngine] = None,
    output_dir: Optional[Path] = None,
) -> list[TrainingSample]:
    """Generate a synthetic training dataset from simulation engine output.

    Args:
        schedules: List of schedule dicts, each containing:
            - route_id: int
            - trip_id: int
            - stops: list[StopTimeEntry]
        engine: SimulationEngine instance (created if not provided)
        output_dir: Directory to write dataset (created if not provided)

    Returns:
        List of TrainingSample observations.

    The synthetic dataset is explicitly NOT real transit data. It is derived
    from the deterministic simulation engine to validate the ML pipeline.
    Real vehicle observations should replace this when available.
    """
    if engine is None:
        engine = SimulationEngine()
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    samples: list[TrainingSample] = []
    now = datetime.now(timezone.utc)

    for schedule_info in schedules:
        route_id = schedule_info["route_id"]
        trip_id = schedule_info["trip_id"]
        stops = schedule_info["stops"]

        if len(stops) < 2:
            continue

        total_duration = stops[-1].arrival_offset_s + SimulationEngine.DEFAULT_DWELL_S

        # Sample across different times of day and days of week
        for day in DAYS_OF_WEEK:
            for time_idx in range(TIME_SAMPLES_PER_TRIP):
                # Generate different elapsed times throughout the trip
                fraction = (time_idx + 1) / (TIME_SAMPLES_PER_TRIP + 1)
                elapsed_s = total_duration * fraction

                # Skip if before departure or past completion
                if elapsed_s <= 0 or elapsed_s >= total_duration:
                    continue

                # Find the segment we're in
                current_stop_idx = 0
                for i, stop in enumerate(stops):
                    if elapsed_s >= stop.arrival_offset_s:
                        current_stop_idx = i
                    else:
                        break

                if current_stop_idx >= len(stops) - 1:
                    continue

                current_stop = stops[current_stop_idx]
                next_stop = stops[current_stop_idx + 1]

                # Scheduled duration for this segment
                segment_scheduled = next_stop.arrival_offset_s - current_stop.arrival_offset_s
                if segment_scheduled <= 0:
                    segment_scheduled = 30  # fallback

                # Simulate actual travel time (deterministic engine output)
                sim_elapsed = elapsed_s - current_stop.arrival_offset_s
                eta_result = engine.compute_eta_at(
                    stops[current_stop_idx:],
                    sim_elapsed,
                )
                if eta_result is None:
                    continue

                # Actual duration: time the simulation engine computes as remaining
                actual_duration = float(eta_result["baseline_eta_seconds"])
                if actual_duration <= 0:
                    continue

                # Distance remaining
                from app.eta.features import _haversine_m
                distance_remaining = _haversine_m(
                    current_stop.lat, current_stop.lon,
                    next_stop.lat, next_stop.lon,
                )

                # Synthetic time-of-day
                hour = 6 + (time_idx * 12 // TIME_SAMPLES_PER_TRIP)
                minute = (time_idx * 30) % 60
                time_of_day = f"{hour:02d}:{minute:02d}"

                sample = TrainingSample(
                    route_id=route_id,
                    stop_id=next_stop.stop_id,
                    time_of_day=time_of_day,
                    day_of_week=day,
                    scheduled_duration_s=segment_scheduled,
                    distance_remaining_m=distance_remaining,
                    delay_seconds=None,
                    actual_duration_s=actual_duration,
                    source=SYNTHETIC_SOURCE,
                    generated_at=now,
                )
                samples.append(sample)

    logger.info(
        "synthetic_dataset_generated",
        sample_count=len(samples),
        route_count=len(set(s["route_id"] for s in schedules)),
    )

    return samples


def save_training_data(
    samples: list[TrainingSample],
    output_dir: Optional[Path] = None,
    filename: str = "synthetic_eta_training_data.json",
) -> Path:
    """Save training samples to a JSON file.

    This is a training artifact, not operational transit data.
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename

    data = {
        "metadata": {
            "source": "synthetic",
            "description": (
                "Synthetic training data generated from deterministic simulation engine. "
                "NOT real transit observations. Used to validate ML pipeline architecture. "
                "Replace with real vehicle observations when available."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sample_count": len(samples),
            "feature_schema": [
                "route_id", "stop_id", "time_of_day", "day_of_week",
                "scheduled_duration_s", "distance_remaining_m", "delay_seconds",
            ],
            "target": "actual_duration_s",
        },
        "samples": [s.model_dump(mode="json") for s in samples],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(
        "training_data_saved",
        filepath=str(filepath),
        sample_count=len(samples),
    )

    return filepath


def load_training_data(
    filepath: Optional[Path] = None,
) -> tuple[list[TrainingSample], dict]:
    """Load training samples from a JSON file.

    Returns:
        Tuple of (samples, metadata).
    """
    if filepath is None:
        filepath = DEFAULT_OUTPUT_DIR / "synthetic_eta_training_data.json"

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    samples = [TrainingSample(**s) for s in data.get("samples", [])]

    logger.info(
        "training_data_loaded",
        filepath=str(filepath),
        sample_count=len(samples),
        source=metadata.get("source", "unknown"),
    )

    return samples, metadata
