from datetime import datetime, time, timezone
from sqlalchemy import select, cast, Time
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.trip import Trip
from app.db.models.route import Route


class TripAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_trips(
        self,
        trips_data: list[dict],
        route_key_to_id: dict[str, int],
    ) -> int:
        imported_count = 0
        for trip_data in trips_data:
            route_id = route_key_to_id.get(self._find_route_key(trip_data["route_id"]))
            if not route_id:
                raise ValueError(f"Route not found for trip: route_id={trip_data['route_id']}")

            existing = await self._get_by_natural_key(route_id, trip_data)
            if existing:
                await self._update(existing, trip_data)
            else:
                await self._create(route_id, trip_data)
            imported_count += 1
        await self.session.flush()
        return imported_count

    def _find_route_key(self, route_uuid: str) -> str:
        route_key_map = {
            "d3cc5779-551f-57f4-9dd5-d10989acdb29": "Red",
            "890d30f3-fc9a-5610-abe4-554545c46b9b": "Orange",
            "9190205e-cd08-50a0-9fb2-c0fa7f27533b": "Blue",
            "51f798dd-bece-53e7-ae87-1f45360ca232": "Green",
            "c79d67e2-dfb4-5109-9f40-3c2b26070258": "FR-01",
            "58e7179b-bcf3-5387-982d-e61cc622d9f7": "FR-03A",
            "0a0217f7-3683-5df2-8ef4-8468d5755364": "FR-04",
            "8840e4b5-4963-540a-a98a-2eaf5da38e7c": "FR-04A",
            "69f9abfe-b4ab-5b1e-982e-1b590325332e": "FR-04B",
            "cd654519-06b3-5ed3-81a4-5899e6fa5456": "FR-05",
            "72095197-1804-51ee-9ca0-bd70c897ea9d": "FR-06",
            "1ce08d52-fc4c-5537-a10c-788784c25578": "FR-07",
            "cd9a2844-6fa3-5905-a5b3-a61a159452a9": "FR-08A",
            "192b7e26-2f5a-55bc-82ac-0510fe82ba51": "FR-08C",
            "6ad1600e-a794-5af4-8e33-9d2acb72556e": "FR-09",
            "ae3136b0-74cb-5608-ab5a-e383006f73ac": "FR-10",
            "fc46dd2c-fa20-5a99-a256-3ae865b71da2": "FR-11",
            "15dd5dd7-1a8c-5fb0-979a-7215a355f37b": "FR-12",
            "92a77ead-ece0-5f14-b46f-8804533e6435": "FR-13",
            "2d82c1c4-c3c7-5267-a454-c096d6bec25c": "FR-14",
            "77f56cb6-75f5-59ab-ada0-cbc9333c3aaf": "FR-14A",
            "6080bbc9-4bc8-5cbf-a059-bb9c0814afa4": "FR-15",
            "31ac4417-1273-5f1d-a7e2-561a4710849a": "FRB-01",
            "0b8fcfde-7efa-53c9-9c9a-86e8b6098cb1": "FRG-1",
            "8223da34-d5ae-5606-9ccc-4393a6c7c12a": "ST-01",
            "e790a940-c51f-5bc9-af09-664bb857d2a9": "ST-02",
        }
        return route_key_map.get(route_uuid, "unknown")

    def _get_direction_id(self, direction: str) -> int | None:
        if direction == "Forward":
            return 0
        elif direction == "Backward":
            return 1
        return None

    def _parse_time(self, time_str: str) -> datetime:
        try:
            t = time.fromisoformat(time_str)
            return datetime(2000, 1, 1, t.hour, t.minute, t.second, t.microsecond, tzinfo=timezone.utc)
        except Exception:
            return datetime(2000, 1, 1, 6, 0, 0, tzinfo=timezone.utc)

    async def _get_by_natural_key(self, route_id: int, trip_data: dict) -> Trip | None:
        direction_id = self._get_direction_id(trip_data.get("direction"))
        t = time.fromisoformat(trip_data.get("canonical_trip_start_time", "06:00:00"))

        result = await self.session.execute(
            select(Trip).where(
                Trip.route_id == route_id,
                Trip.direction_id == direction_id,
                cast(Trip.scheduled_start_time, Time) == t,
            )
        )
        return result.scalar_one_or_none()

    async def _create(self, route_id: int, data: dict) -> Trip:
        direction_id = self._get_direction_id(data.get("direction"))
        scheduled_start = self._parse_time(data.get("canonical_trip_start_time", "06:00:00"))

        trip = Trip(
            route_id=route_id,
            direction_id=direction_id,
            headsign=data.get("long_name") or data.get("short_name"),
            scheduled_start_time=scheduled_start,
            status="scheduled",
        )
        self.session.add(trip)
        return trip

    async def _update(self, trip: Trip, data: dict) -> Trip:
        trip.direction_id = self._get_direction_id(data.get("direction"))
        trip.headsign = data.get("long_name") or data.get("short_name")
        trip.scheduled_start_time = self._parse_time(data.get("canonical_trip_start_time", "06:00:00"))
        trip.status = "scheduled"
        return trip


async def import_trips(
    session: AsyncSession,
    trips_data: list[dict],
    route_key_to_id: dict[str, int],
) -> int:
    adapter = TripAdapter(session)
    return await adapter.import_trips(trips_data, route_key_to_id)