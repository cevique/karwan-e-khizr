from typing import Protocol
from pydantic import BaseModel


class PaymentResult(BaseModel):
    success: bool
    transaction_id: str | None = None
    error_message: str | None = None


class PaymentProvider(Protocol):
    async def process_payment(
        self, user_id: int, amount: float, currency: str
    ) -> PaymentResult: ...