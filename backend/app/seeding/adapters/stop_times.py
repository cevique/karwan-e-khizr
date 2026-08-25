from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.stop_time import StopTime
from app.db.models.trip import Trip
from app.db.models.stop import Stop


class StopTimeAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_stop_times(
        self,
        trips_data: list[dict],
        route_key_to_id: dict[str, int],
        stop_key_to_id: dict[str, int],
        stop_uuid_to_key: dict[str, str],
    ) -> int:
        imported_count = 0
        for trip_data in trips_data:
            route_id = route_key_to_id.get(self._find_route_key(trip_data["route_id"]))
            if not route_id:
                continue

            trip = await self._get_trip_by_route_and_pattern(route_id, trip_data)
            if not trip:
                continue

            for idx, st_data in enumerate(trip_data.get("stop_times", [])):
                stop_key = stop_uuid_to_key.get(st_data["stop_id"])
                stop_id = stop_key_to_id.get(stop_key) if stop_key else None
                if not stop_id:
                    continue

                existing = await self._get_by_trip_stop(trip.id, stop_id)
                if existing:
                    await self._update(existing, st_data, idx)
                else:
                    await self._create(trip.id, stop_id, st_data, idx)
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

    async def _get_trip_by_route_and_pattern(self, route_id: int, trip_data: dict) -> Trip | None:
        from app.seeding.adapters.trips import TripAdapter
        adapter = TripAdapter(self.session)
        direction_id = adapter._get_direction_id(trip_data.get("direction"))
        scheduled_start = adapter._parse_time(trip_data.get("canonical_trip_start_time", "06:00:00"))

        result = await self.session.execute(
            select(Trip).where(
                Trip.route_id == route_id,
                Trip.direction_id == direction_id,
                Trip.scheduled_start_time == scheduled_start,
            )
        )
        return result.scalar_one_or_none()

    async def _get_by_trip_stop(self, trip_id: int, stop_id: int) -> StopTime | None:
        result = await self.session.execute(
            select(StopTime).where(
                StopTime.trip_id == trip_id,
                StopTime.stop_id == stop_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create(self, trip_id: int, stop_id: int, data: dict, sequence: int) -> StopTime:
        arrival_offset = data.get("arrival_offset_s", 0)
        departure_offset = data.get("departure_offset_s")
        # If departure is None, use arrival offset (as per canonical dataset)
        if departure_offset is None:
            departure_offset = arrival_offset

        st = StopTime(
            trip_id=trip_id,
            stop_id=stop_id,
            sequence=sequence,
            arrival_offset_s=arrival_offset,
            departure_offset_s=departure_offset,
        )
        self.session.add(st)
        return st

    async def _update(self, st: StopTime, data: dict, sequence: int) -> StopTime:
        st.sequence = sequence
        st.arrival_offset_s = data.get("arrival_offset_s", 0)
        departure_offset = data.get("departure_offset_s")
        if departure_offset is None:
            departure_offset = st.arrival_offset_s
        st.departure_offset_s = departure_offset
        return st


async def import_stop_times(
    session: AsyncSession,
    trips_data: list[dict],
    route_key_to_id: dict[str, int],
    stop_key_to_id: dict[str, int],
    stop_uuid_to_key: dict[str, str],
) -> int:
    adapter = StopTimeAdapter(session)
    return await adapter.import_stop_times(trips_data, route_key_to_id, stop_key_to_id, stop_uuid_to_key)