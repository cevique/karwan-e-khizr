import asyncio
from sqlalchemy import text
from app.core.database import init_db, AsyncSessionLocal


async def check():
    await init_db()
    async with AsyncSessionLocal() as s:
        # Check actual stop rows (not route_stops) for duplicates
        r = await s.execute(text("""
            SELECT id, name, ST_Y(location) as lat, ST_X(location) as lon
            FROM stops
            WHERE name IN (
                SELECT name FROM stops WHERE location IS NOT NULL
                GROUP BY name HAVING COUNT(*) > 1
            )
            ORDER BY name, id
        """))
        print("=== Actual stop rows for duplicate names ===")
        for row in r:
            print(f"  {row[0]}: {row[1]} @ ({row[2]:.6f}, {row[3]:.6f})")

        # Check how many stops have NO location
        r2 = await s.execute(text("""
            SELECT id, name FROM stops WHERE location IS NULL ORDER BY name
        """))
        no_loc = r2.fetchall()
        print(f"\n=== Stops without location ({len(no_loc)}) ===")
        for row in no_loc[:15]:
            print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    asyncio.run(check())
