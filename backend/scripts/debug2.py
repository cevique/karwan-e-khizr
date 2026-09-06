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
        result = await session.execute(
            select(Trip).where(
                Trip.status.in_(["scheduled", "active"]),
                Trip.scheduled_start_time <= now,
            )
        )
        trips = result.scalars().all()
        print(f"NOW: {now.isoformat()}")
        print(f"Trips: {len(trips)}")

        for trip in trips:
            st_result = await session.execute(
                select(StopTime).where(StopTime.trip_id == trip.id).order_by(StopTime.sequence)
            )
            st_list = st_result.scalars().all()
            if not st_list:
                print(f"  trip {trip.id}: NO STOP_TIMES")
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

            if not entries:
                print(f"  trip {trip.id}: NO ENTRIES after location lookup")
                continue

            elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
            total_duration = entries[-1].arrival_offset_s + 15
            print(f"  trip {trip.id}: elapsed={elapsed_s:.0f}s total_dur={total_duration}s last_arrival={entries[-1].arrival_offset_s}")

asyncio.run(debug())
