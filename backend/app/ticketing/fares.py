from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fare_rule import FareRule
from app.routing.schemas import FareQuote
from app.core.constants import DEFAULT_BASE_FARE, DEFAULT_PER_LEG_FARE, CURRENCY


class FaresService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_fare_quote(self, ride_leg_count: int) -> FareQuote:
        result = await self.session.execute(
            select(FareRule).where(FareRule.is_active == True).order_by(FareRule.id)
        )
        fare_rule = result.scalars().first()

        if fare_rule is None:
            base_fare = DEFAULT_BASE_FARE
            per_leg_fare = DEFAULT_PER_LEG_FARE
        else:
            base_fare = fare_rule.base_fare
            per_leg_fare = fare_rule.per_leg_fare

        if ride_leg_count <= 0:
            total = 0.0
        elif ride_leg_count == 1:
            total = base_fare
        else:
            total = base_fare + per_leg_fare * (ride_leg_count - 1)

        return FareQuote(
            base_fare=base_fare,
            per_leg_fare=per_leg_fare,
            total=total,
            currency=CURRENCY,
        )