"""Update stops without coordinates with researched locations, then snap to road."""
import asyncio
import httpx

OSRM_NEAREST_URL = "http://router.project-osrm.org/nearest/v1/driving"

# Coordinates from subagent research
COORDS = {
    118099: (33.707, 73.087),
    118132: (33.665, 73.000),
    118133: (33.660, 73.178),
    118131: (33.684, 72.989),
    118073: (33.719, 73.092),
    118118: (33.690, 73.043),
    118180: (33.620, 72.973),
    118123: (33.696, 73.011),
    118174: (33.628, 73.011),
    118223: (33.533, 73.179),
    118222: (33.530, 73.167),
    118137: (33.710, 73.103),
    118164: (33.697, 73.003),
    118143: (33.661, 73.083),
    118192: (33.724, 73.083),
    118193: (33.641, 72.962),
    118052: (33.642, 72.965),
    118181: (33.642, 72.965),
    118183: (33.640, 72.960),
    118169: (33.691, 72.974),
    118194: (33.683, 73.025),
    118182: (33.620, 72.985),
    118150: (33.696, 73.038),
    118070: (33.656, 73.071),
    118162: (33.692, 73.010),
    118163: (33.690, 73.003),
    118082: (33.673, 73.038),
    118128: (33.688, 73.028),
    118142: (33.688, 73.043),
    118221: (33.545, 73.177),
    118145: (33.649, 73.052),
    118146: (33.646, 73.052),
    118178: (33.625, 73.010),
    118141: (33.672, 73.106),
    118072: (33.665, 73.065),
    118130: (33.613, 72.994),
    118081: (33.660, 73.064),
    118197: (33.668, 72.978),
    118187: (33.722, 73.035),
    118056: (33.549, 72.826),
    118196: (33.720, 73.060),
    118074: (33.658, 73.058),
    118215: (33.650, 73.070),
    118159: (33.730, 73.085),
    118040: (33.685, 73.048),
    118144: (33.652, 73.064),
    118177: (33.632, 73.039),
    118071: (33.661, 73.066),
    118095: (33.645, 73.050),
    118139: (33.694, 73.123),
    118093: (33.620, 73.100),
    118109: (33.727, 73.107),
    118218: (33.570, 73.120),
    118219: (33.565, 73.115),
    118075: (33.655, 73.055),
    118126: (33.640, 73.045),
    118207: (33.741, 72.786),
    118209: (33.600, 73.060),
    118064: (33.625, 73.105),
}


async def snap_to_road(lat, lon, client):
    try:
        url = f"{OSRM_NEAREST_URL}/{lon},{lat}"
        r = await client.get(url, timeout=5)
        data = r.json()
        if data.get("code") == "Ok" and data.get("waypoints"):
            wp = data["waypoints"][0]
            snapped_lon, snapped_lat = wp["location"]
            return snapped_lat, snapped_lon
    except Exception:
        pass
    return None


async def main():
    from sqlalchemy import text
    from app.core.database import init_db, AsyncSessionLocal

    await init_db()
    async with AsyncSessionLocal() as session:
        updated = 0
        async with httpx.AsyncClient() as client:
            for stop_id, (lat, lon) in COORDS.items():
                snapped = await snap_to_road(lat, lon, client)
                if snapped:
                    lat, lon = snapped
                await session.execute(
                    text("UPDATE stops SET location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) WHERE id = :id"),
                    {"lon": lon, "lat": lat, "id": stop_id}
                )
                updated += 1
                await asyncio.sleep(0.2)

        await session.commit()
        print(f"Updated {updated} stops")

        # Verify
        r = await session.execute(text("SELECT COUNT(*) FROM stops WHERE location IS NULL"))
        remaining = r.scalar()
        print(f"Stops still without location: {remaining}")


if __name__ == "__main__":
    asyncio.run(main())
