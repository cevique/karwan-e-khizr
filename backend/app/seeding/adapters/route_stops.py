from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.route_stop import RouteStop
from app.db.models.route import Route
from app.db.models.stop import Stop


class RouteStopAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_route_stops(
        self,
        route_stops_data: list[dict],
        route_key_to_id: dict[str, int],
        stop_key_to_id: dict[str, int],
        stop_uuid_to_key: dict[str, str],
    ) -> int:
        imported_count = 0
        for rs_data in route_stops_data:
            route_id = route_key_to_id.get(self._find_route_key(rs_data["route_id"]))
            stop_key = stop_uuid_to_key.get(rs_data["stop_id"])
            stop_id = stop_key_to_id.get(stop_key) if stop_key else None

            if not route_id or not stop_id:
                raise ValueError(
                    f"Route or stop not found for route_stop: route_id={rs_data['route_id']}, stop_id={rs_data['stop_id']}, stop_key={stop_key}"
                )

            existing = await self._get_by_route_stop(route_id, stop_id)
            if existing:
                await self._update(existing, rs_data)
            else:
                await self._create(route_id, stop_id, rs_data)
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

    async def _get_by_route_stop(self, route_id: int, stop_id: int) -> RouteStop | None:
        result = await self.session.execute(
            select(RouteStop).where(
                RouteStop.route_id == route_id,
                RouteStop.stop_id == stop_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create(self, route_id: int, stop_id: int, data: dict) -> RouteStop:
        rs = RouteStop(
            route_id=route_id,
            stop_id=stop_id,
            sequence=data["sequence"],
            distance_along_route_m=data.get("distance_along_route_m"),
        )
        self.session.add(rs)
        return rs

    async def _update(self, rs: RouteStop, data: dict) -> RouteStop:
        rs.sequence = data["sequence"]
        rs.distance_along_route_m = data.get("distance_along_route_m")
        return rs


async def import_route_stops(
    session: AsyncSession,
    route_stops_data: list[dict],
    route_key_to_id: dict[str, int],
    stop_key_to_id: dict[str, int],
    stop_uuid_to_key: dict[str, str],
) -> int:
    adapter = RouteStopAdapter(session)
    return await adapter.import_route_stops(route_stops_data, route_key_to_id, stop_key_to_id, stop_uuid_to_key)