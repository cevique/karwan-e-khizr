from app.payments.provider import PaymentProvider, PaymentResult


class MockPaymentProvider:
    """Always succeeds — no real transaction."""

    async def process_payment(
        self, user_id: int, amount: float, currency: str
    ) -> PaymentResult:
        return PaymentResult(success=True, transaction_id=f"mock_tx_{user_id}_{int(amount * 100)}")