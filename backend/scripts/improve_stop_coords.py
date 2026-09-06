"""
Improve stop coordinates by:
1. Using Nominatim to find actual bus stop locations (with "bus stop" in query)
2. Snapping to nearest road point using OSRM
"""
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
    """Snap a point to the nearest road using OSRM."""
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
    from geoalchemy2.shape import to_shape

    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Stop).where(Stop.location.isnot(None)).order_by(Stop.name)
        )
        stops = result.scalars().all()
        print(f"Total stops with location: {len(stops)}")

        updated_nominatim = 0
        updated_road = 0
        failed = 0

        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        ) as client:
            for i, stop in enumerate(stops):
                point = to_shape(stop.location)
                old_lat, old_lon = point.y, point.x

                # Try to find a more specific location via Nominatim
                # Search for the stop as a bus stop
                query = f"{stop.name} bus stop Islamabad Pakistan"
                coords = await nominatim_search(query, client)

                if not coords:
                    query = f"{stop.name} bus stop Rawalpindi Pakistan"
                    coords = await nominatim_search(query, client)

                if not coords:
                    # Try just the name with city
                    query = f"{stop.name} Islamabad Pakistan"
                    coords = await nominatim_search(query, client)

                new_lat, new_lon = old_lat, old_lon
                if coords:
                    new_lat, new_lon = coords
                    if abs(new_lat - old_lat) > 0.001 or abs(new_lon - old_lon) > 0.001:
                        updated_nominatim += 1

                # Snap to nearest road point
                snapped = await snap_to_road(new_lat, new_lon, client)
                if snapped:
                    snap_lat, snap_lon = snapped
                    # Only use snapped if it's within 500m of original
                    # (to avoid snapping to a completely wrong road)
                    import math
                    dlat = snap_lat - new_lat
                    dlon = snap_lon - new_lon
                    dist_m = math.sqrt((dlat * 111320) ** 2 + (dlon * 111320 * math.cos(math.radians(new_lat))) ** 2)
                    if dist_m < 500:
                        new_lat, new_lon = snap_lat, snap_lon
                        updated_road += 1

                # Update DB
                await session.execute(
                    text("UPDATE stops SET location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) WHERE id = :id"),
                    {"lon": new_lon, "lat": new_lat, "id": stop.id}
                )

                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i + 1}/{len(stops)} (nominatim={updated_nominatim} road_snapped={updated_road} failed={failed})")
                    await asyncio.sleep(1.1)
                else:
                    await asyncio.sleep(1.1)

            await session.commit()
            print(f"\nDone: {updated_nominatim} nominatim updates, {updated_road} road snaps, {failed} failed")


if __name__ == "__main__":
    asyncio.run(main())
