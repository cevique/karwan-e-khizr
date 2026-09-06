import asyncio
from sqlalchemy import select, func
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.stop import Stop


async def check():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stop).limit(5))
        stops = result.scalars().all()
        for s in stops:
            print(f"Stop {s.id}: name={s.name} location={s.location} type={type(s.location)}")

asyncio.run(check())
