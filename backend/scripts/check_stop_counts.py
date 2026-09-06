import asyncio
from sqlalchemy import select, func, text
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.stop import Stop


async def check():
    await init_db()
    async with AsyncSessionLocal() as session:
        total = await session.scalar(select(func.count(Stop.id)))
        with_loc = await session.scalar(
            select(func.count(Stop.id)).where(Stop.location.isnot(None))
        )
        without_loc = await session.scalar(
            select(func.count(Stop.id)).where(Stop.location.is_(None))
        )
        print(f"Total stops: {total}")
        print(f"With location: {with_loc}")
        print(f"Without location: {without_loc}")

        # Check external_keys
        result = await session.execute(select(Stop.external_key).limit(20))
        keys = [r[0] for r in result.all()]
        print(f"Sample external_keys: {keys}")

asyncio.run(check())
