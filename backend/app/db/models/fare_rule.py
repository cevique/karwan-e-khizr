from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FareRule(Base):
    __tablename__ = "fare_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_fare: Mapped[float] = mapped_column(nullable=False)
    per_leg_fare: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)