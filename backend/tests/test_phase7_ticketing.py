import pytest
import json
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.core.database import init_db, AsyncSessionLocal, close_db
from app.core.config import settings
from app.core.constants import DEFAULT_BASE_FARE, DEFAULT_PER_LEG_FARE, TICKET_EXPIRY_HOURS
from app.core.security import create_access_token
from app.db.models.fare_rule import FareRule
from app.db.models.user import User
from app.db.models.ticket import Ticket
from app.ticketing.fares import FaresService
from app.ticketing.qr import QRService, QRVerificationResult
from app.ticketing.service import TicketService
from app.ticketing.schemas import (
    FareQuoteRequest,
    FareQuote,
    TicketPurchaseRequest,
    TicketResponse,
    TicketListResponse,
    ValidationRequest,
    ValidationResult,
)
from app.payments.provider import PaymentResult
from app.payments.mock import MockPaymentProvider
from app.main import create_app


@pytest.fixture(scope="function")
async def db_session():
    await init_db()
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM tickets"))
        await session.execute(text("DELETE FROM fare_rules"))
        await session.execute(text("DELETE FROM users"))
        await session.commit()
        yield session
    await close_db()


@pytest.fixture(scope="function")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


# ─── Unit Tests: FaresService ─────────────────────────────────────────────────


class TestFaresService:
    @pytest.mark.asyncio
    async def test_fare_calculation_with_db_rule(self, db_session):
        """Fare is read from FareRule table."""
        fare_rule = FareRule(
            name="Standard Metrobus",
            base_fare=50.0,
            per_leg_fare=20.0,
            currency="PKR",
            is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = FaresService(db_session)
        quote = await service.get_fare_quote(ride_leg_count=2)
        assert quote.base_fare == 50.0
        assert quote.per_leg_fare == 20.0
        assert quote.total == 70.0
        assert quote.currency == "PKR"

    @pytest.mark.asyncio
    async def test_fare_calculation_default_fallback(self, db_session):
        """When no FareRule exists, uses hardcoded defaults."""
        # Ensure no active fare rules
        result = await db_session.execute(select(FareRule).where(FareRule.is_active == True))
        for rule in result.scalars().all():
            await db_session.delete(rule)
        await db_session.commit()

        service = FaresService(db_session)
        quote = await service.get_fare_quote(ride_leg_count=3)
        assert quote.base_fare == DEFAULT_BASE_FARE
        assert quote.per_leg_fare == DEFAULT_PER_LEG_FARE
        assert quote.total == DEFAULT_BASE_FARE + DEFAULT_PER_LEG_FARE * 2
        assert quote.currency == "PKR"

    @pytest.mark.asyncio
    async def test_fare_zero_ride_legs(self, db_session):
        """All-walking journey (0 ride legs) returns 0 fare."""
        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = FaresService(db_session)
        quote = await service.get_fare_quote(ride_leg_count=0)
        assert quote.total == 0.0

    @pytest.mark.asyncio
    async def test_fare_single_leg(self, db_session):
        """Single ride leg: total = base_fare."""
        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = FaresService(db_session)
        quote = await service.get_fare_quote(ride_leg_count=1)
        assert quote.total == 50.0

    @pytest.mark.asyncio
    async def test_fare_multiple_legs(self, db_session):
        """Multiple ride legs: base + per_leg * (n-1)."""
        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = FaresService(db_session)
        quote = await service.get_fare_quote(ride_leg_count=5)
        assert quote.total == 50.0 + 20.0 * 4

    @pytest.mark.asyncio
    async def test_fare_inactive_rule_ignored(self, db_session):
        """Inactive fare rules are not used."""
        inactive = FareRule(
            name="Old", base_fare=100.0, per_leg_fare=50.0,
            currency="PKR", is_active=False,
        )
        db_session.add(inactive)
        await db_session.commit()

        service = FaresService(db_session)
        quote = await service.get_fare_quote(ride_leg_count=2)
        # Should fall back to defaults
        assert quote.base_fare == DEFAULT_BASE_FARE
        assert quote.per_leg_fare == DEFAULT_PER_LEG_FARE


# ─── Unit Tests: QRService ────────────────────────────────────────────────────


class TestQRService:
    def setup_method(self):
        self.qr = QRService()

    def test_generate_and_verify_roundtrip(self):
        """QR payload generation and verification round-trips correctly."""
        token = self.qr.generate_payload(ticket_id=42, user_id=7)
        result = self.qr.verify_payload(token)
        assert result.valid is True
        assert result.ticket_id == 42
        assert result.user_id == 7
        assert result.error is None

    def test_tampered_payload_rejected(self):
        """Tampered QR payload is rejected."""
        token = self.qr.generate_payload(ticket_id=42, user_id=7)
        # Tamper with the base64 content
        tampered = token[:-5] + "XXXXX"
        result = self.qr.verify_payload(tampered)
        assert result.valid is False
        assert result.error is not None

    def test_wrong_signing_key_rejected(self):
        """QR signed with different key is rejected."""
        token = self.qr.generate_payload(ticket_id=42, user_id=7)
        # Verify with original key
        result = self.qr.verify_payload(token)
        assert result.valid is True

        # Swap QR_SIGNING_KEY and try again
        original_key = settings.QR_SIGNING_KEY
        settings.QR_SIGNING_KEY = "completely_different_key_123456"
        try:
            qr2 = QRService()
            result2 = qr2.verify_payload(token)
            assert result2.valid is False
        finally:
            settings.QR_SIGNING_KEY = original_key

    def test_expired_token_rejected(self):
        """Expired QR token is rejected."""
        # Create QRService, generate token, then mock expiry in the past
        token = self.qr.generate_payload(ticket_id=42, user_id=7)

        # Manually create a token with past expiry
        import base64
        payload = {"ticket_id": 42, "user_id": 7, "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp())}
        signature = self.qr._create_signature(payload)
        token_data = {"p": payload, "s": signature}
        token_json = json.dumps(token_data, separators=(",", ":"))
        token_b64 = base64.urlsafe_b64encode(token_json.encode()).decode().rstrip("=")

        result = self.qr.verify_payload(token_b64)
        assert result.valid is False
        assert "expired" in result.error.lower()

    def test_missing_expiry_rejected(self):
        """Token without expiry is rejected."""
        import base64
        payload = {"ticket_id": 42, "user_id": 7}
        signature = self.qr._create_signature(payload)
        token_data = {"p": payload, "s": signature}
        token_json = json.dumps(token_data, separators=(",", ":"))
        token_b64 = base64.urlsafe_b64encode(token_json.encode()).decode().rstrip("=")

        result = self.qr.verify_payload(token_b64)
        assert result.valid is False
        assert "missing expiry" in result.error.lower()

    def test_malformed_token_rejected(self):
        """Malformed token string is rejected."""
        result = self.qr.verify_payload("not_a_valid_token!!!")
        assert result.valid is False

    def test_missing_fields_rejected(self):
        """Token without ticket_id or user_id is rejected."""
        import base64
        payload = {"exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())}
        signature = self.qr._create_signature(payload)
        token_data = {"p": payload, "s": signature}
        token_json = json.dumps(token_data, separators=(",", ":"))
        token_b64 = base64.urlsafe_b64encode(token_json.encode()).decode().rstrip("=")

        result = self.qr.verify_payload(token_b64)
        assert result.valid is False


# ─── Unit Tests: MockPaymentProvider ──────────────────────────────────────────


class TestMockPaymentProvider:
    @pytest.mark.asyncio
    async def test_always_succeeds(self):
        provider = MockPaymentProvider()
        result = await provider.process_payment(user_id=1, amount=70.0, currency="PKR")
        assert result.success is True
        assert result.transaction_id is not None


# ─── Unit Tests: TicketSchemas ────────────────────────────────────────────────


class TestTicketSchemas:
    def test_fare_quote_request(self):
        req = FareQuoteRequest(ride_leg_count=2)
        assert req.ride_leg_count == 2

    def test_fare_quote_request_min(self):
        req = FareQuoteRequest(ride_leg_count=0)
        assert req.ride_leg_count == 0

    def test_fare_quote_request_max(self):
        req = FareQuoteRequest(ride_leg_count=10)
        assert req.ride_leg_count == 10

    def test_fare_quote_request_invalid_negative(self):
        with pytest.raises(Exception):
            FareQuoteRequest(ride_leg_count=-1)

    def test_fare_quote_request_invalid_over_max(self):
        with pytest.raises(Exception):
            FareQuoteRequest(ride_leg_count=11)

    def test_ticket_purchase_request(self):
        req = TicketPurchaseRequest(
            journey_data={"legs": []},
            ride_leg_count=2,
        )
        assert req.journey_data == {"legs": []}
        assert req.ride_leg_count == 2

    def test_ticket_purchase_request_invalid_zero(self):
        with pytest.raises(Exception):
            TicketPurchaseRequest(journey_data={}, ride_leg_count=0)


# ─── Integration Tests: TicketService ────────────────────────────────────────


class TestTicketService:
    @pytest.mark.asyncio
    async def test_purchase_ticket_creates_active_ticket(self, db_session):
        """Ticket purchase creates an ACTIVE ticket with correct fare and QR."""
        user = User(
            email="test@example.com",
            hashed_password="hashed",
            role="passenger",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        request = TicketPurchaseRequest(
            journey_data={"legs": [{"type": "ride", "route_id": 1}]},
            ride_leg_count=2,
        )
        ticket = await service.purchase_ticket(user.id, request)

        assert ticket.id is not None
        assert ticket.status == "ACTIVE"
        assert ticket.fare_charged == 70.0
        assert ticket.currency == "PKR"
        assert ticket.qr_payload is not None
        assert ticket.ride_leg_count == 2
        assert ticket.journey_data == {"legs": [{"type": "ride", "route_id": 1}]}
        assert ticket.expires_at is not None
        assert ticket.created_at is not None

    @pytest.mark.asyncio
    async def test_purchase_ticket_calls_payment_provider(self, db_session):
        """Ticket purchase processes payment via PaymentProvider."""
        user = User(
            email="test2@example.com",
            hashed_password="hashed",
            role="passenger",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        with patch.object(service.payment_provider, 'process_payment', new_callable=AsyncMock) as mock_pay:
            mock_pay.return_value = PaymentResult(success=True, transaction_id="mock_123")
            request = TicketPurchaseRequest(
                journey_data={"legs": []},
                ride_leg_count=1,
            )
            ticket = await service.purchase_ticket(user.id, request)
            mock_pay.assert_called_once()

    @pytest.mark.asyncio
    async def test_purchase_ticket_payment_failure(self, db_session):
        """Ticket purchase fails when payment fails."""
        user = User(
            email="test3@example.com",
            hashed_password="hashed",
            role="passenger",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = TicketService(db_session)
        with patch.object(service.payment_provider, 'process_payment', new_callable=AsyncMock) as mock_pay:
            mock_pay.return_value = PaymentResult(success=False, error_message="Card declined")
            request = TicketPurchaseRequest(
                journey_data={"legs": []},
                ride_leg_count=1,
            )
            with pytest.raises(Exception, match="Payment failed"):
                await service.purchase_ticket(user.id, request)

    @pytest.mark.asyncio
    async def test_get_ticket_ownership_enforced(self, db_session):
        """Only the ticket owner can retrieve their ticket."""
        user1 = User(
            email="user1@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        user2 = User(
            email="user2@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        request = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user1.id, request)

        # Owner can get
        retrieved = await service.get_ticket(ticket.id, user1.id)
        assert retrieved.id == ticket.id

        # Non-owner cannot get
        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await service.get_ticket(ticket.id, user2.id)

    @pytest.mark.asyncio
    async def test_list_tickets_only_returns_own(self, db_session):
        """List tickets returns only the authenticated user's tickets."""
        user1 = User(
            email="user1b@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        user2 = User(
            email="user2b@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        await service.purchase_ticket(user1.id, req)
        await service.purchase_ticket(user1.id, req)
        await service.purchase_ticket(user2.id, req)

        list1 = await service.list_tickets(user1.id)
        list2 = await service.list_tickets(user2.id)
        assert len(list1.tickets) == 2
        assert len(list2.tickets) == 1


# ─── Integration Tests: Ticket Validation ────────────────────────────────────


class TestTicketValidation:
    @pytest.mark.asyncio
    async def test_successful_validation_transitions_to_used(self, db_session):
        """Successful validation transitions ACTIVE ticket to USED."""
        user = User(
            email="val1@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        # Validate
        result = await service.validate_ticket(ticket.qr_payload, user.id)
        assert result.valid is True
        assert result.ticket_id == ticket.id
        assert result.status == "USED"

        # Verify DB state
        db_ticket = await db_session.get(Ticket, ticket.id)
        assert db_ticket.status == "USED"
        assert db_ticket.used_at is not None

    @pytest.mark.asyncio
    async def test_double_validation_rejected(self, db_session):
        """Second validation of the same ticket is rejected (replay protection)."""
        user = User(
            email="double@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        # First validation succeeds
        result1 = await service.validate_ticket(ticket.qr_payload, user.id)
        assert result1.valid is True

        # Second validation fails
        result2 = await service.validate_ticket(ticket.qr_payload, user.id)
        assert result2.valid is False
        assert "used" in result2.reason.lower()

    @pytest.mark.asyncio
    async def test_validate_revoked_ticket(self, db_session):
        """REVOKED ticket cannot be validated."""
        user = User(
            email="revoked@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        # Revoke
        await service.revoke_ticket(ticket.id, user.id)

        # Validate fails
        result = await service.validate_ticket(ticket.qr_payload, user.id)
        assert result.valid is False
        assert "revoked" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_validate_expired_ticket(self, db_session):
        """EXPIRED ticket cannot be validated (lazy expiry)."""
        user = User(
            email="expired@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        # Force ticket to be expired by setting expires_at in the past
        db_ticket = await db_session.get(Ticket, ticket.id)
        db_ticket.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db_session.commit()

        # Validate fails with lazy expiry
        result = await service.validate_ticket(ticket.qr_payload, user.id)
        assert result.valid is False
        assert "expired" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_validate_tampered_qr_rejected(self, db_session):
        """Tampered QR payload is rejected."""
        user = User(
            email="tampered@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        # Tamper with QR
        tampered = ticket.qr_payload[:-5] + "XXXXX"
        result = await service.validate_ticket(tampered, user.id)
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_concurrent_validation_exactly_one_succeeds(self, db_session):
        """Two concurrent validations of the same ticket — exactly one succeeds."""
        user = User(
            email="concurrent@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        # Launch two concurrent validations using separate sessions
        results = []
        async def validate_task(session, qr_payload, uid):
            svc = TicketService(session)
            r = await svc.validate_ticket(qr_payload, uid)
            results.append(r.valid)

        async with AsyncSessionLocal() as session1, AsyncSessionLocal() as session2:
            await asyncio.gather(
                validate_task(session1, ticket.qr_payload, user.id),
                validate_task(session2, ticket.qr_payload, user.id),
            )

        # Exactly one should have succeeded
        assert results.count(True) == 1
        assert results.count(False) == 1


# ─── Integration Tests: Ticket Revocation ────────────────────────────────────


class TestTicketRevocation:
    @pytest.mark.asyncio
    async def test_revoke_active_ticket(self, db_session):
        """Owner can revoke their ACTIVE ticket."""
        user = User(
            email="revoke@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        result = await service.revoke_ticket(ticket.id, user.id)
        assert result.status == "REVOKED"

    @pytest.mark.asyncio
    async def test_revoke_used_ticket_fails(self, db_session):
        """Cannot revoke a USED ticket."""
        user = User(
            email="revoke_used@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user.id, req)

        # Validate first
        await service.validate_ticket(ticket.qr_payload, user.id)

        # Try to revoke
        from app.core.exceptions import ConflictError
        with pytest.raises(ConflictError, match="Cannot revoke"):
            await service.revoke_ticket(ticket.id, user.id)

    @pytest.mark.asyncio
    async def test_revoke_other_users_ticket_fails(self, db_session):
        """Cannot revoke another user's ticket."""
        user1 = User(
            email="revoke_u1@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        user2 = User(
            email="revoke_u2@example.com", hashed_password="hashed",
            role="passenger", is_active=True,
        )
        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        fare_rule = FareRule(
            name="Standard", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        db_session.add(fare_rule)
        await db_session.commit()

        service = TicketService(db_session)
        req = TicketPurchaseRequest(journey_data={"legs": []}, ride_leg_count=1)
        ticket = await service.purchase_ticket(user1.id, req)

        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await service.revoke_ticket(ticket.id, user2.id)


# ─── Unit Tests: Schemas ─────────────────────────────────────────────────────


class TestTicketSchemasValidation:
    def test_ticket_response_schema(self):
        resp = TicketResponse(
            id=1,
            status="ACTIVE",
            fare_charged=70.0,
            currency="PKR",
            qr_payload="abc123",
            created_at=datetime.now(UTC),
            ride_leg_count=2,
            journey_data={},
        )
        assert resp.id == 1
        assert resp.status == "ACTIVE"

    def test_validation_result_schema(self):
        vr = ValidationResult(valid=True, ticket_id=1, status="USED")
        assert vr.valid is True

    def test_fare_quote_schema(self):
        fq = FareQuote(base_fare=50.0, per_leg_fare=20.0, total=70.0, currency="PKR")
        assert fq.total == 70.0


# ─── Regression Tests: Phase 1-6 ────────────────────────────────────────────


class TestPhaseRegressions:
    def test_fare_rule_model_fields(self):
        """FareRule model has required fields."""
        rule = FareRule(
            name="Test", base_fare=50.0, per_leg_fare=20.0,
            currency="PKR", is_active=True,
        )
        assert rule.name == "Test"
        assert rule.base_fare == 50.0
        assert rule.per_leg_fare == 20.0
        assert rule.currency == "PKR"
        assert rule.is_active is True

    def test_ticket_model_fields(self):
        """Ticket model has required fields."""
        ticket = Ticket(
            user_id=1,
            journey_data={},
            ride_leg_count=1,
            fare_charged=50.0,
            currency="PKR",
            status="ACTIVE",
            qr_payload="test",
        )
        assert ticket.user_id == 1
        assert ticket.status == "ACTIVE"

    def test_user_model_fields(self):
        """User model has required fields."""
        user = User(
            email="test@test.com",
            hashed_password="hashed",
            role="passenger",
            is_active=True,
        )
        assert user.email == "test@test.com"
        assert user.role == "passenger"