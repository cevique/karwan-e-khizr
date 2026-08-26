from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routing.engine import JourneySearchEngine
from app.routing.schemas import (
    JourneySearchRequest,
    JourneySearchResponse,
    AmbiguousLocationResponse,
    NoRouteFoundResponse,
)

router = APIRouter(prefix="/transit/journeys", tags=["journeys"])


@router.post("/search", status_code=status.HTTP_200_OK)
async def search_journeys(
    request: JourneySearchRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    engine = JourneySearchEngine(session)
    result = await engine.search(
        origin=request.origin,
        destination=request.destination,
        objective=request.objective,
        max_walk_m=request.max_walk_m,
        max_transfers=request.max_transfers,
        departure_time=request.departure_time,
    )

    if isinstance(result, AmbiguousLocationResponse):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.model_dump(),
        )
    elif isinstance(result, NoRouteFoundResponse):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.model_dump(),
        )

    return result