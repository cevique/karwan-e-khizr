from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.router import api_router
from app.core.config import settings, validate_required_settings
from app.core.database import close_db, init_db
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting up", environment=settings.APP_ENV)

    validate_required_settings()

    await init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down")
    await close_db()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Karwan-e-Khizr Transit API",
        description="Backend API for Islamabad/Rawalpindi transit journey planning",
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    )

    cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code, **exc.details},
        )

    return app


app = create_app()