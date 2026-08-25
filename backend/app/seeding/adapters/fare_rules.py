from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fare_rule import FareRule


class FareRuleAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_fare_rules(self, fare_rules_data: list[dict]) -> int:
        imported_count = 0
        for fr_data in fare_rules_data:
            existing = await self._get_by_name(fr_data["name"])
            if existing:
                await self._update(existing, fr_data)
            else:
                await self._create(fr_data)
            imported_count += 1
        await self.session.flush()
        return imported_count

    async def _get_by_name(self, name: str) -> FareRule | None:
        result = await self.session.execute(
            select(FareRule).where(FareRule.name == name)
        )
        return result.scalar_one_or_none()

    async def _create(self, data: dict) -> FareRule:
        fr = FareRule(
            name=data["name"],
            base_fare=data["base_fare"],
            per_leg_fare=data["per_leg_fare"],
            currency=data.get("currency", "PKR"),
            is_active=data.get("is_active", True),
        )
        self.session.add(fr)
        return fr

    async def _update(self, fr: FareRule, data: dict) -> FareRule:
        fr.base_fare = data["base_fare"]
        fr.per_leg_fare = data["per_leg_fare"]
        fr.currency = data.get("currency", "PKR")
        fr.is_active = data.get("is_active", True)
        return fr


async def import_fare_rules(session: AsyncSession, fare_rules_data: list[dict]) -> int:
    adapter = FareRuleAdapter(session)
    return await adapter.import_fare_rules(fare_rules_data)