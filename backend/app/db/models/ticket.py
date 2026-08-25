from datetime import datetime
from sqlalchemy import ForeignKey, String, Enum as SQLEnum, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    journey_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ride_leg_count: Mapped[int] = mapped_column(nullable=False)
    fare_charged: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")
    status: Mapped[str] = mapped_column(SQLEnum("ACTIVE", "USED", "EXPIRED", "REVOKED", name="ticket_status_enum"), nullable=False, default="ACTIVE")
    qr_payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", backref="tickets")