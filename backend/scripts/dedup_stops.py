"""Remove duplicate stops (same name + same coords) by merging stop_times too."""
import asyncio
from sqlalchemy import text
from app.core.database import init_db, AsyncSessionLocal


async def dedup():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Find true duplicates (same name, same coords rounded to 5 decimals)
        r = await session.execute(text("""
            SELECT name, ROUND(ST_Y(location)::numeric, 5) as lat,
                   ROUND(ST_X(location)::numeric, 5) as lon,
                   array_agg(id ORDER BY id) as ids
            FROM stops
            WHERE location IS NOT NULL
            GROUP BY name, ROUND(ST_Y(location)::numeric, 5), ROUND(ST_X(location)::numeric, 5)
            HAVING COUNT(*) > 1
        """))
        true_dups = r.fetchall()
        print(f"True duplicates (same name + coords): {len(true_dups)}")

        removed = 0
        for name, lat, lon, ids in true_dups:
            keep_id = ids[0]
            remove_ids = ids[1:]
            print(f"  Keeping {keep_id}, removing {remove_ids} for '{name}'")

            for rid in remove_ids:
                # Move stop_times to the kept stop
                await session.execute(text("""
                    UPDATE stop_times SET stop_id = :keep
                    WHERE stop_id = :remove
                    AND NOT EXISTS (
                        SELECT 1 FROM stop_times st2
                        WHERE st2.stop_id = :keep AND st2.trip_id = stop_times.trip_id
                        AND st2.sequence = stop_times.sequence
                    )
                """), {"keep": keep_id, "remove": rid})

                # Delete remaining stop_times (duplicates)
                await session.execute(text("DELETE FROM stop_times WHERE stop_id = :id"), {"id": rid})

                # Move route_stops to kept stop
                await session.execute(text("""
                    UPDATE route_stops SET stop_id = :keep
                    WHERE stop_id = :remove
                    AND NOT EXISTS (
                        SELECT 1 FROM route_stops rs2
                        WHERE rs2.stop_id = :keep AND rs2.route_id = route_stops.route_id
                    )
                """), {"keep": keep_id, "remove": rid})

                # Delete remaining route_stops
                await session.execute(text("DELETE FROM route_stops WHERE stop_id = :id"), {"id": rid})

                # Delete the duplicate stop
                await session.execute(text("DELETE FROM stops WHERE id = :id"), {"id": rid})
                removed += 1

        await session.commit()
        print(f"Removed {removed} true duplicate stops")

        # Show remaining same-name stops (different locations)
        r2 = await session.execute(text("""
            SELECT name, count(*) as cnt
            FROM stops WHERE location IS NOT NULL
            GROUP BY name HAVING COUNT(*) > 1
        """))
        name_dups = r2.fetchall()
        print(f"\nRemaining same-name stops at different locations: {len(name_dups)}")
        for name, cnt in name_dups:
            print(f"  '{name}' x{cnt}")


if __name__ == "__main__":
    asyncio.run(dedup())
