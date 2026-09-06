import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.db.models.vehicle import Vehicle
from app.simulation.engine import SimulationEngine
from app.simulation.schemas import StopTimeEntry
from geoalchemy2.shape import to_shape

async def diagnose():
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
        print(f"Trips matching query filter: {len(trips)}")

        engine = SimulationEngine()
        for trip in trips:
            stops_result = await session.execute(
                select(StopTime).where(StopTime.trip_id == trip.id).order_by(StopTime.sequence)
            )
            stop_times_db = stops_result.scalars().all()

            entries = []
            for st in stop_times_db:
                from app.db.models.stop import Stop
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
                print(f"  trip {trip.id}: NO ENTRIES")
                continue

            elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
            total_duration = entries[-1].arrival_offset_s + 15
            skip1 = elapsed_s < -300
            skip2 = elapsed_s > total_duration + 60
            pos = engine.compute_position_at(entries, elapsed_s)
            print(f"  trip {trip.id}: elapsed={elapsed_s:.0f}s dur={total_duration}s skip_past={skip1} skip_done={skip2} status={pos['status']} lat={pos['latitude']:.4f}")

            vehicle = Vehicle(label=f"Test-{trip.id}", route_id=trip.route_id, trip_id=trip.id, status="active")
            session.add(vehicle)
        await session.commit()
        print("Committed test vehicles")

asyncio.run(diagnose())
