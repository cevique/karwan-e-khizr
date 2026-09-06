import asyncio
import json
from sqlalchemy import select, text
from app.core.database import init_db, AsyncSessionLocal
from app.db.models.stop import Stop


async def fix():
    await init_db()
    async with AsyncSessionLocal() as session:
        with open("data/transit_data.json") as f:
            data = json.load(f)

        json_by_key = {s["key"]: s for s in data["stops"]}
        json_by_name = {s["name"]: s for s in data["stops"]}

        result = await session.execute(select(Stop))
        stops = result.scalars().all()

        updated = 0
        not_found = 0
        for stop in stops:
            sd = json_by_key.get(stop.external_key) or json_by_name.get(stop.name)
            if sd and sd.get("latitude") and sd.get("longitude"):
                await session.execute(
                    text("UPDATE stops SET location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) WHERE id = :id"),
                    {"lon": sd["longitude"], "lat": sd["latitude"], "id": stop.id}
                )
                updated += 1
            else:
                not_found += 1
                if not_found <= 5:
                    print(f"  NOT FOUND: id={stop.id} key={stop.external_key} name={stop.name}")

        await session.commit()
        print(f"Updated {updated}/{len(stops)} stops ({not_found} not matched)")

asyncio.run(fix())
