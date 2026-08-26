from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.journeys import router as journeys_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="", tags=["health"])
api_router.include_router(journeys_router, prefix="", tags=["journeys"])