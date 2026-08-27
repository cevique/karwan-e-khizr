from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import rate_limit_dependency
from app.users.dependencies import CurrentUser
from app.ticketing.service import TicketService
from app.ticketing.schemas import (
    FareQuoteRequest,
    FareQuote,
    TicketPurchaseRequest,
    TicketResponse,
    TicketListResponse,
    ValidationRequest,
    ValidationResult,
    RevokeRequest,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])
fares_router = APIRouter(prefix="/fares", tags=["fares"])

_validate_limiter_dep, _validate_limiter = rate_limit_dependency(
    max_requests=settings.RATE_LIMIT_VALIDATE, window_seconds=60
)


@fares_router.post("/quote", response_model=FareQuote, status_code=status.HTTP_200_OK)
async def get_fare_quote(
    request: FareQuoteRequest,
    session: AsyncSession = Depends(get_db),
) -> FareQuote:
    """Get a fare quote for a journey with the given number of ride legs."""
    service = TicketService(session)
    return await service.get_fare_quote(request.ride_leg_count)


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def purchase_ticket(
    request: TicketPurchaseRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Purchase a ticket for a journey."""
    service = TicketService(session)
    return await service.purchase_ticket(current_user.id, request)


@router.get("", response_model=TicketListResponse, status_code=status.HTTP_200_OK)
async def list_tickets(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> TicketListResponse:
    """List all tickets for the current user."""
    service = TicketService(session)
    return await service.list_tickets(current_user.id)


@router.get("/{ticket_id}", response_model=TicketResponse, status_code=status.HTTP_200_OK)
async def get_ticket(
    ticket_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Get a specific ticket by ID."""
    service = TicketService(session)
    try:
        return await service.get_ticket(ticket_id, current_user.id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        raise


@router.post("/{ticket_id}/revoke", response_model=TicketResponse, status_code=status.HTTP_200_OK)
async def revoke_ticket(
    ticket_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Revoke an ACTIVE ticket."""
    service = TicketService(session)
    try:
        return await service.revoke_ticket(ticket_id, current_user.id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        if "cannot revoke" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise


@router.post(
    "/validate",
    response_model=ValidationResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_validate_limiter_dep)],
)
async def validate_ticket(
    request: ValidationRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ValidationResult:
    """Validate a QR ticket."""
    service = TicketService(session)
    return await service.validate_ticket(request.qr_payload, current_user.id)