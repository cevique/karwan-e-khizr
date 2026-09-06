import asyncio
from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime


async def fix_stop_times():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Trip).order_by(Trip.id))
        trips = result.scalars().all()

        total_updated = 0
        for trip in trips:
            st_result = await session.execute(
                select(StopTime).where(StopTime.trip_id == trip.id).order_by(StopTime.sequence)
            )
            stop_times = st_result.scalars().all()
            if not stop_times:
                continue

            cumulative_s = 0
            dwell_s = 15
            inter_stop_s = 90

            for i, st in enumerate(stop_times):
                st.arrival_offset_s = cumulative_s
                cumulative_s += dwell_s
                st.departure_offset_s = cumulative_s

                if i < len(stop_times) - 1:
                    cumulative_s += inter_stop_s

                total_updated += 1

        await session.commit()
        print(f"Updated {total_updated} stop_time records across {len(trips)} trips")


if __name__ == "__main__":
    asyncio.run(fix_stop_times())
