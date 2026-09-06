import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.simulation.engine import SimulationEngine


async def check():
    await init_db()
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(select(Trip).order_by(Trip.id))
        trips = result.scalars().all()
        
        for trip in trips:
            result2 = await session.execute(
                select(StopTime).where(StopTime.trip_id == trip.id).order_by(StopTime.sequence)
            )
            stops = result2.scalars().all()
            if not stops:
                print(f"trip {trip.id}: NO STOPS")
                continue
            total_duration = stops[-1].arrival_offset_s + 15
            elapsed_s = (now - trip.scheduled_start_time.replace(tzinfo=timezone.utc)).total_seconds()
            status_ok = trip.status in ("scheduled", "active")
            past_filter = elapsed_s >= -300
            duration_filter = elapsed_s <= total_duration + 60
            print(f"trip {trip.id} status={trip.status} elapsed={elapsed_s:.0f}s duration={total_duration}s status_ok={status_ok} past={past_filter} dur={duration_filter} -> {'PASS' if status_ok and past_filter and duration_filter else 'SKIP'}")


if __name__ == "__main__":
    asyncio.run(check())
