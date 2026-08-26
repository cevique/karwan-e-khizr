from datetime import datetime, timedelta, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.ticket import Ticket
from app.db.models.user import User
from app.ticketing.fares import FaresService
from app.ticketing.qr import QRService, QRVerificationResult
from app.ticketing.schemas import (
    FareQuote,
    TicketPurchaseRequest,
    TicketResponse,
    TicketListResponse,
    ValidationRequest,
    ValidationResult,
)
from app.payments.mock import MockPaymentProvider
from app.core.constants import TICKET_EXPIRY_HOURS, CURRENCY
from app.core.exceptions import NotFoundError, ConflictError


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.fares_service = FaresService(session)
        self.qr_service = QRService()
        self.payment_provider = MockPaymentProvider()

    async def get_fare_quote(self, ride_leg_count: int) -> FareQuote:
        """Get a fare quote for the given number of ride legs."""
        return await self.fares_service.get_fare_quote(ride_leg_count)

    async def purchase_ticket(
        self, user_id: int, purchase_request: TicketPurchaseRequest
    ) -> TicketResponse:
        """
        Purchase a ticket for a journey.
        
        1. Compute fare server-side from ride_leg_count
        2. Process payment via PaymentProvider
        3. Generate signed QR payload
        4. Persist ticket with ACTIVE status
        """
        # Verify user exists
        user = await self.session.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        # Compute fare server-side (never trust client-supplied fare)
        fare_quote = await self.fares_service.get_fare_quote(purchase_request.ride_leg_count)

        # Process payment
        payment_result = await self.payment_provider.process_payment(
            user_id=user_id,
            amount=fare_quote.total,
            currency=fare_quote.currency,
        )
        if not payment_result.success:
            raise ConflictError(f"Payment failed: {payment_result.error_message}")

        # Generate QR payload
        # We need to create the ticket first to get its ID, then generate QR with that ID
        # But QR needs ticket_id... so we'll create ticket, flush to get ID, then update QR
        expires_at = datetime.now(UTC) + timedelta(hours=TICKET_EXPIRY_HOURS)

        # Create ticket with placeholder QR (will update after flush)
        ticket = Ticket(
            user_id=user_id,
            journey_data=purchase_request.journey_data,
            ride_leg_count=purchase_request.ride_leg_count,
            fare_charged=fare_quote.total,
            currency=fare_quote.currency,
            status="ACTIVE",
            qr_payload="",  # placeholder
            created_at=datetime.now(UTC),
            expires_at=expires_at,
            used_at=None,
        )
        self.session.add(ticket)
        await self.session.flush()  # Get ticket ID

        # Now generate QR with actual ticket ID
        qr_payload = self.qr_service.generate_payload(ticket.id, user_id)
        ticket.qr_payload = qr_payload

        await self.session.commit()
        await self.session.refresh(ticket)

        return self._ticket_to_response(ticket)

    async def get_ticket(self, ticket_id: int, user_id: int) -> TicketResponse:
        """Get a specific ticket by ID, ensuring ownership."""
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.user_id == user_id)
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError("Ticket not found")
        return self._ticket_to_response(ticket)

    async def list_tickets(self, user_id: int) -> TicketListResponse:
        """List all tickets for the current user."""
        result = await self.session.execute(
            select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
        )
        tickets = result.scalars().all()
        return TicketListResponse(tickets=[self._ticket_to_response(t) for t in tickets])

    async def validate_ticket(self, qr_payload: str, validator_user_id: int) -> ValidationResult:
        """
        Validate a QR ticket atomically.
        
        1. Verify QR signature
        2. Extract ticket_id, user_id
        3. Check ownership (QR user_id matches ticket owner)
        4. Check ticket status (must be ACTIVE)
        5. Transition to USED in a single transaction
        6. Return VALID/INVALID
        """
        # Verify QR signature
        verification = self.qr_service.verify_payload(qr_payload)
        if not verification.valid:
            return ValidationResult(
                valid=False,
                reason=verification.error or "Invalid QR payload",
            )

        ticket_id = verification.ticket_id
        qr_user_id = verification.user_id

        # Check ownership: QR user_id must match the validator's user_id
        # Actually, the validator could be a different user (e.g., conductor)
        # The important check is that the ticket belongs to the QR user_id
        # and the validator is authorized (has a valid JWT)
        # The spec says: "Ownership must be enforced: a ticket's owner and the QR's 
        # claimed owner must match (a tamper check)."
        # So we just verify ticket.user_id == qr_user_id

        # Fetch ticket with row-level lock for atomic update
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id).with_for_update()
        )
        ticket = result.scalar_one_or_none()

        if not ticket:
            return ValidationResult(
                valid=False,
                ticket_id=ticket_id,
                reason="Ticket not found",
            )

        # Verify ownership (tamper check)
        if ticket.user_id != qr_user_id:
            return ValidationResult(
                valid=False,
                ticket_id=ticket_id,
                reason="Ownership mismatch",
            )

        # Check effective status (lazy expiry)
        effective_status = self._get_effective_status(ticket)
        if effective_status != "ACTIVE":
            return ValidationResult(
                valid=False,
                ticket_id=ticket_id,
                status=effective_status,
                reason=f"Ticket is {effective_status.lower()}",
            )

        # Atomic transition to USED
        ticket.status = "USED"
        ticket.used_at = datetime.now(UTC)
        
        await self.session.commit()

        return ValidationResult(
            valid=True,
            ticket_id=ticket_id,
            status="USED",
        )

    async def revoke_ticket(self, ticket_id: int, user_id: int) -> TicketResponse:
        """Revoke a ticket (user can revoke their own ACTIVE ticket)."""
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.user_id == user_id)
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError("Ticket not found")

        if ticket.status != "ACTIVE":
            raise ConflictError(f"Cannot revoke ticket with status {ticket.status}")

        ticket.status = "REVOKED"
        await self.session.commit()
        await self.session.refresh(ticket)

        return self._ticket_to_response(ticket)

    def _get_effective_status(self, ticket: Ticket) -> str:
        """Get effective ticket status considering lazy expiry."""
        if ticket.status == "ACTIVE" and ticket.expires_at:
            if datetime.now(UTC) > ticket.expires_at:
                return "EXPIRED"
        return ticket.status

    def _ticket_to_response(self, ticket: Ticket) -> TicketResponse:
        effective_status = self._get_effective_status(ticket)
        return TicketResponse(
            id=ticket.id,
            status=effective_status,
            fare_charged=ticket.fare_charged,
            currency=ticket.currency,
            qr_payload=ticket.qr_payload,
            created_at=ticket.created_at,
            expires_at=ticket.expires_at,
            used_at=ticket.used_at,
            ride_leg_count=ticket.ride_leg_count,
            journey_data=ticket.journey_data,
        )