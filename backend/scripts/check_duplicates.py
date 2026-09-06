import asyncio
from sqlalchemy import text
from app.core.database import init_db, AsyncSessionLocal


async def check():
    await init_db()
    async with AsyncSessionLocal() as s:
        # For each duplicate name, check which routes they serve
        r = await s.execute(text("""
            SELECT s.name, s.id, rs.route_id, r.short_name, ST_Y(s.location) as lat, ST_X(s.location) as lon
            FROM stops s
            JOIN route_stops rs ON rs.stop_id = s.id
            JOIN routes r ON r.id = rs.route_id
            WHERE s.name IN (
                SELECT name FROM stops WHERE location IS NOT NULL
                GROUP BY name HAVING COUNT(*) > 1
            )
            ORDER BY s.name, s.id
        """))
        print("=== Duplicate stops by route ===")
        current_name = None
        for row in r:
            if row[0] != current_name:
                current_name = row[0]
                print(f"\n  {current_name}:")
            print(f"    Stop {row[1]} -> Route {row[3]} ({row[2]}) @ ({row[4]:.6f}, {row[5]:.6f})")


if __name__ == "__main__":
    asyncio.run(check())
