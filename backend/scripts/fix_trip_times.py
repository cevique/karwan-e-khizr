import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime


async def fix():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Trip).order_by(Trip.id))
        trips = result.scalars().all()

        now = datetime.now(timezone.utc)

        for i, trip in enumerate(trips):
            result2 = await session.execute(
                select(StopTime)
                .where(StopTime.trip_id == trip.id)
                .order_by(StopTime.sequence.desc())
                .limit(1)
            )
            last_stop = result2.scalars().first()

            if last_stop:
                trip_duration_s = last_stop.arrival_offset_s + 15
            else:
                trip_duration_s = 1800

            spread_minutes = (i * 7) % 120
            start_offset = timedelta(minutes=spread_minutes) - timedelta(seconds=trip_duration_s // 3)

            new_start = now + start_offset
            trip.scheduled_start_time = new_start

        await session.commit()
        print(f"Updated {len(trips)} trips with current timestamps")


if __name__ == "__main__":
    asyncio.run(fix())
