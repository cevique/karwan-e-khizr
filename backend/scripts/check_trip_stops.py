import asyncio
from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.db.models.stop import Stop


async def check():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Trip).order_by(Trip.id))
        trips = result.scalars().all()

        used_stop_ids = set()
        for trip in trips:
            st_result = await session.execute(
                select(StopTime.stop_id).where(StopTime.trip_id == trip.id)
            )
            for (sid,) in st_result.all():
                used_stop_ids.add(sid)

        print(f"Trips: {len(trips)}")
        print(f"Unique stops used by trips: {len(used_stop_ids)}")

        for sid in sorted(used_stop_ids):
            stop = await session.get(Stop, sid)
            has_loc = stop.location is not None if stop else False
            print(f"  stop {sid}: {stop.name if stop else '?'} key={stop.external_key if stop else '?'} has_loc={has_loc}")

asyncio.run(check())
