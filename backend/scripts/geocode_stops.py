import asyncio
import httpx
from sqlalchemy import select, text
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.stop import Stop

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "karwan-e-khizr-qa/1.0 (transit-app-testing)"


async def geocode(name: str, client: httpx.AsyncClient) -> tuple[float, float] | None:
    try:
        r = await client.get(NOMINATIM_URL, params={
            "q": name,
            "format": "json",
            "limit": 1,
            "countrycodes": "pk",
        })
        results = r.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None


async def fix():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Stop).where(Stop.location.is_(None))
        )
        stops = result.scalars().all()
        print(f"Stops needing geocoding: {len(stops)}")

        updated = 0
        failed = 0
        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=10) as client:
            for i, stop in enumerate(stops):
                query = f"{stop.name}, Islamabad, Pakistan"
                coords = await geocode(query, client)

                if not coords:
                    query2 = f"{stop.name}, Rawalpindi, Pakistan"
                    coords = await geocode(query2, client)

                if coords:
                    lat, lon = coords
                    await session.execute(
                        text("UPDATE stops SET location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) WHERE id = :id"),
                        {"lon": lon, "lat": lat, "id": stop.id}
                    )
                    updated += 1
                else:
                    failed += 1

                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i + 1}/{len(stops)} (updated={updated} failed={failed})")
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(1.1)

            await session.commit()
            print(f"Done: updated {updated}/{len(stops)} stops ({failed} failed)")


if __name__ == "__main__":
    asyncio.run(fix())
