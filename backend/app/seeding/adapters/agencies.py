import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agency import Agency


class AgencyAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_agencies(self, agencies_data: list[dict]) -> int:
        imported_count = 0
        for agency_data in agencies_data:
            existing = await self._get_by_key(agency_data["key"])
            if existing:
                await self._update(existing, agency_data)
            else:
                await self._create(agency_data)
            imported_count += 1
        await self.session.flush()
        return imported_count

    async def _get_by_key(self, key: str) -> Agency | None:
        result = await self.session.execute(
            select(Agency).where(Agency.short_name == key)
        )
        return result.scalar_one_or_none()

    async def _create(self, data: dict) -> Agency:
        agency = Agency(
            name=data["name"],
            short_name=data["key"],
            url=None,
            timezone="Asia/Karachi",
        )
        self.session.add(agency)
        return agency

    async def _update(self, agency: Agency, data: dict) -> Agency:
        agency.name = data["name"]
        agency.short_name = data["key"]
        agency.timezone = "Asia/Karachi"
        return agency


async def import_agencies(session: AsyncSession, agencies_data: list[dict]) -> int:
    adapter = AgencyAdapter(session)
    return await adapter.import_agencies(agencies_data)