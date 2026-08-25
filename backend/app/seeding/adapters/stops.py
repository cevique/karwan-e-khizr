import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import WKTElement

from app.db.models.stop import Stop


class StopAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_stops(self, stops_data: list[dict]) -> int:
        imported_count = 0
        for stop_data in stops_data:
            existing = await self._get_by_key(stop_data["key"])
            if existing:
                await self._update(existing, stop_data)
            else:
                await self._create(stop_data)
            imported_count += 1
        await self.session.flush()
        return imported_count

    async def _get_by_key(self, key: str) -> Stop | None:
        result = await self.session.execute(
            select(Stop).where(Stop.name == key)
        )
        return result.scalar_one_or_none()

    async def _create(self, data: dict) -> Stop:
        location = None
        if data.get("latitude") is not None and data.get("longitude") is not None:
            location = WKTElement(
                f"POINT({data['longitude']} {data['latitude']})", srid=4326
            )

        coordinate_source = self._map_coordinate_source(data.get("source", ""), data.get("confidence", ""))
        coordinate_confidence = self._map_coordinate_confidence(data.get("confidence", ""))

        stop = Stop(
            name=data["key"],
            location=location,
            coordinate_source=coordinate_source,
            coordinate_confidence=coordinate_confidence,
            zone_id=None,
        )
        self.session.add(stop)
        return stop

    async def _update(self, stop: Stop, data: dict) -> Stop:
        location = None
        if data.get("latitude") is not None and data.get("longitude") is not None:
            location = WKTElement(
                f"POINT({data['longitude']} {data['latitude']})", srid=4326
            )

        coordinate_source = self._map_coordinate_source(data.get("source", ""), data.get("confidence", ""))
        coordinate_confidence = self._map_coordinate_confidence(data.get("confidence", ""))

        stop.location = location
        stop.coordinate_source = coordinate_source
        stop.coordinate_confidence = coordinate_confidence
        return stop

    def _map_coordinate_source(self, source: str, confidence: str) -> str | None:
        source_lower = source.lower()
        if "official" in source_lower or confidence == "OFFICIAL":
            return "curated"
        elif "nominatim" in source_lower or "openstreetmap" in source_lower:
            return "nominatim"
        elif "repo-curated" in source_lower or "seed_dataset" in source_lower:
            return "curated"
        elif confidence == "UNKNOWN" or "not established" in source_lower or "not yet surveyed" in source_lower:
            return "UNKNOWN"
        return None

    def _map_coordinate_confidence(self, confidence: str) -> str | None:
        conf = confidence.upper()
        if conf in ("HIGH", "VERIFIED", "OFFICIAL"):
            return "HIGH"
        elif conf in ("APPROXIMATE", "RECONSTRUCTED", "INFERRED"):
            return "APPROXIMATE"
        elif conf == "UNKNOWN":
            return "UNKNOWN"
        return None


async def import_stops(session: AsyncSession, stops_data: list[dict]) -> int:
    adapter = StopAdapter(session)
    return await adapter.import_stops(stops_data)