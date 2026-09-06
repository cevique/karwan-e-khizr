"""Geocode remaining stops without coordinates, then snap to road."""
import asyncio
import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_NEAREST_URL = "http://router.project-osrm.org/nearest/v1/driving"
USER_AGENT = "karwan-e-khizr-qa/1.0 (transit-app-testing)"


async def nominatim_search(query: str, client: httpx.AsyncClient) -> tuple[float, float] | None:
    try:
        r = await client.get(NOMINATIM_URL, params={
            "q": query,
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


async def snap_to_road(lat: float, lon: float, client: httpx.AsyncClient) -> tuple[float, float] | None:
    try:
        url = f"{OSRM_NEAREST_URL}/{lon},{lat}"
        r = await client.get(url)
        data = r.json()
        if data.get("code") == "Ok" and data.get("waypoints"):
            wp = data["waypoints"][0]
            snapped_lon, snapped_lat = wp["location"]
            return snapped_lat, snapped_lon
    except Exception:
        pass
    return None


async def main():
    from sqlalchemy import select, text
    from app.core.database import init_db, AsyncSessionLocal
    from app.db.models.stop import Stop

    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Stop).where(Stop.location.is_(None)).order_by(Stop.name)
        )
        stops = result.scalars().all()
        print(f"Stops without location: {len(stops)}")

        updated = 0
        failed = 0

        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        ) as client:
            for i, stop in enumerate(stops):
                # Try Islamabad first, then Rawalpindi
                for city in ["Islamabad", "Rawalpindi"]:
                    coords = await nominatim_search(f"{stop.name}, {city}, Pakistan", client)
                    if coords:
                        break
                    await asyncio.sleep(1.1)

                if coords:
                    lat, lon = coords
                    snapped = await snap_to_road(lat, lon, client)
                    if snapped:
                        lat, lon = snapped
                    await session.execute(
                        text("UPDATE stops SET location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) WHERE id = :id"),
                        {"lon": lon, "lat": lat, "id": stop.id}
                    )
                    updated += 1
                else:
                    failed += 1
                    print(f"  FAILED: {stop.name} (ID {stop.id})")

                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i + 1}/{len(stops)} (updated={updated} failed={failed})")

                await asyncio.sleep(1.1)

            await session.commit()
            print(f"\nDone: updated {updated}/{len(stops)} ({failed} failed)")


if __name__ == "__main__":
    asyncio.run(main())
