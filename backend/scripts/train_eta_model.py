"""Train the ETA prediction model using simulation engine data."""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.db.models.route import Route
from app.db.models.route_stop import RouteStop
from app.db.models.stop import Stop
from app.db.models.stop_time import StopTime
from app.db.models.trip import Trip
from app.eta.model import train_model, save_model
from app.eta.training import generate_synthetic_dataset
from app.simulation.engine import SimulationEngine
from app.simulation.schemas import StopTimeEntry
from geoalchemy2.shape import to_shape


async def main():
    engine = SimulationEngine()

    async with AsyncSessionLocal() as session:
        # Load all trips with their schedules
        trips = (await session.execute(select(Trip))).scalars().all()
        schedules = []

        for trip in trips:
            stop_times = (await session.execute(
                select(StopTime)
                .where(StopTime.trip_id == trip.id)
                .order_by(StopTime.sequence)
            )).scalars().all()

            if len(stop_times) < 2:
                continue

            stops = []
            for st in stop_times:
                stop = await session.get(Stop, st.stop_id)
                if stop and stop.location is not None:
                    point = to_shape(stop.location)
                    stops.append(StopTimeEntry(
                        stop_id=st.stop_id,
                        sequence=st.sequence,
                        arrival_offset_s=float(st.arrival_offset_s),
                        departure_offset_s=float(st.departure_offset_s),
                        lat=point.y,
                        lon=point.x,
                    ))

            if len(stops) >= 2:
                schedules.append({
                    "route_id": trip.route_id,
                    "trip_id": trip.id,
                    "stops": stops,
                })

    print(f"Loaded {len(schedules)} schedules with stops")

    # Generate synthetic dataset
    samples = generate_synthetic_dataset(schedules, engine)
    print(f"Generated {len(samples)} synthetic training samples")

    # Train model
    if len(samples) < 10:
        print("Not enough samples to train. Need at least 10.")
        return

    result = train_model(samples, model_version="v1")

    # Save model
    model_dir = save_model(result, version="v1")
    print(f"Model saved to {model_dir}")

    # Print evaluation
    if result.evaluation:
        if result.evaluation.get("lightgbm"):
            lgb = result.evaluation["lightgbm"]
            print(f"LightGBM: MAE={lgb['mae']:.1f}s, RMSE={lgb['rmse']:.1f}s, R²={lgb['r2']:.3f}")
        lr = result.evaluation["linear"]
        print(f"Linear: MAE={lr['mae']:.1f}s, RMSE={lr['rmse']:.1f}s, R²={lr['r2']:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
