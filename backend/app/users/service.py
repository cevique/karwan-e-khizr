from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, email: str, password: str, full_name: str | None = None) -> User:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Email already registered")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role="passenger",
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, email: str, password: str) -> tuple[str, User]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        token = create_access_token(subject=str(user.id), role=user.role)
        return token, user

    async def get_by_id(self, user_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def get_by_id_or_none(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
