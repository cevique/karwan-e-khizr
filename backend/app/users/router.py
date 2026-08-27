from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import rate_limit_dependency
from app.users.dependencies import CurrentUser
from app.users.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserPublic,
)
from app.users.service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

_login_limiter_dep, _login_limiter = rate_limit_dependency(
    max_requests=settings.RATE_LIMIT_LOGIN, window_seconds=60
)
_register_limiter_dep, _register_limiter = rate_limit_dependency(
    max_requests=settings.RATE_LIMIT_REGISTER, window_seconds=60
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    dependencies=[Depends(_register_limiter_dep)],
)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
    service = UserService(db)
    user = await service.register(email=request.email, password=request.password, full_name=request.full_name)
    return RegisterResponse(id=user.id, email=user.email, role=user.role)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(_login_limiter_dep)],
)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    service = UserService(db)
    token, user = await service.login(email=request.email, password=request.password)
    user_public = UserPublic(id=user.id, email=user.email, full_name=user.full_name, role=user.role)
    return LoginResponse(access_token=token, user=user_public)


@router.get("/me", response_model=UserPublic)
async def get_me(user: CurrentUser) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, full_name=user.full_name, role=user.role)
