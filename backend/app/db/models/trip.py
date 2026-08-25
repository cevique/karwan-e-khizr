from datetime import datetime
from sqlalchemy import ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    direction_id: Mapped[int | None] = mapped_column(nullable=True)
    headsign: Mapped[str | None] = mapped_column(nullable=True)
    scheduled_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(SQLEnum("scheduled", "active", "completed", "cancelled", name="trip_status_enum"), nullable=False, default="scheduled")

    route: Mapped["Route"] = relationship("Route", backref="trips")