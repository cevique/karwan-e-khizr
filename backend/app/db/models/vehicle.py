from sqlalchemy import ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(nullable=False)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"), nullable=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"), nullable=True)
    status: Mapped[str] = mapped_column(SQLEnum("scheduled", "active", "completed", name="vehicle_status_enum"), nullable=False, default="scheduled")

    route: Mapped["Route"] = relationship("Route", backref="vehicles")
    trip: Mapped["Trip"] = relationship("Trip", backref="vehicles")