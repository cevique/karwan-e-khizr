from datetime import datetime
from sqlalchemy import ForeignKey, Enum as SQLEnum, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VehiclePosition(Base):
    __tablename__ = "vehicle_positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    bearing: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(SQLEnum("simulated", "realtime", name="position_source_enum"), nullable=False)

    vehicle: Mapped["Vehicle"] = relationship("Vehicle", backref="positions")