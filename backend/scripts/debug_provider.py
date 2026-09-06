import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.db.models.stop import Stop
from app.simulation.engine import SimulationEngine
from app.simulation.schemas import StopTimeEntry
from geoalchemy2.shape import to_shape


async def debug():
    await init_db()
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        print(f"NOW: {now.isoformat()}")

        # Exact same query as provider
        result = await session.execute(
            select(Trip).where(
                Trip.status.in_(["scheduled", "active"]),
                Trip.scheduled_start_time <= now,
            )
        )
        trips = result.scalars().all()
        print(f"Trips matching provider filter: {len(trips)}")

        engine = SimulationEngine()
        for trip in trips:
            # Load stop times
            st_result = await session.execute(
                select(StopTime).where(StopTime.trip_id == trip.id).order_by(StopTime.sequence)
            )
            st_list = st_result.scalars().all()
            if not st_list:
                print(f"  trip {trip.id}: no stop_times")
                continue

            entries = []
            for st in st_list:
                stop = await session.get(Stop, st.stop_id)
                if stop is None or stop.location is None:
                    continue
                point = to_shape(stop.location)
                entries.append(StopTimeEntry(
                    stop_id=st.stop_id, sequence=st.sequence,
                    arrival_offset_s=st.arrival_offset_s, departure_offset_s=st.departure_offset_s,
                    lat=point.y, lon=point.x,
                ))

            elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
            total_duration = entries[-1].arrival_offset_s + engine.DEFAULT_DWELL_S if entries else 0

            skip1 = elapsed_s < -300
            skip2 = elapsed_s > total_duration + 60

            if skip1 or skip2:
                print(f"  trip {trip.id}: SKIPPED elapsed={elapsed_s:.0f}s total={total_duration}s skip_past={skip1} skip_done={skip2}")
                continue

            pos = engine.compute_position_at(entries, elapsed_s)
            print(f"  trip {trip.id}: lat={pos['latitude']:.4f} lon={pos['longitude']:.4f} status={pos['status']} speed={pos['speed']:.1f}")

asyncio.run(debug())
