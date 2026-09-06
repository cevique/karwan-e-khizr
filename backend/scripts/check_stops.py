import asyncio
from sqlalchemy import text
from app.core.database import init_db, AsyncSessionLocal


async def check():
    await init_db()
    async with AsyncSessionLocal() as s:
        r = await s.execute(text("""
            SELECT name, COUNT(*) as cnt
            FROM stops
            WHERE location IS NOT NULL
            GROUP BY name
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            LIMIT 20
        """))
        print("=== Duplicate stop names ===")
        for row in r:
            print(f'  "{row[0]}" x{row[1]}')

        r2 = await s.execute(text("SELECT COUNT(*) FROM stops WHERE location IS NOT NULL"))
        with_coords = r2.scalar()
        r3 = await s.execute(text("SELECT COUNT(*) FROM stops"))
        total = r3.scalar()
        print(f"\nTotal stops: {total}, with coords: {with_coords}")

        r4 = await s.execute(text("""
            SELECT s.id, s.name, ST_Y(s.location) as lat, ST_X(s.location) as lon
            FROM stops s
            WHERE s.location IS NOT NULL
            ORDER BY s.name
            LIMIT 15
        """))
        print("\n=== Sample stops ===")
        for row in r4:
            print(f"  {row[0]}: {row[1]} -> ({row[2]:.6f}, {row[3]:.6f})")


if __name__ == "__main__":
    asyncio.run(check())
