from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.journeys import router as journeys_router
from app.users.router import router as auth_router
from app.ticketing.router import router as tickets_router, fares_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="", tags=["health"])
api_router.include_router(journeys_router, prefix="", tags=["journeys"])
api_router.include_router(auth_router, prefix="", tags=["auth"])
api_router.include_router(fares_router, prefix="", tags=["fares"])
api_router.include_router(tickets_router, prefix="", tags=["tickets"])