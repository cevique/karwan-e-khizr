from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StopTime(Base):
    __tablename__ = "stop_times"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)
    arrival_offset_s: Mapped[int] = mapped_column(nullable=False)
    departure_offset_s: Mapped[int] = mapped_column(nullable=False)

    trip: Mapped["Trip"] = relationship("Trip", backref="stop_times")
    stop: Mapped["Stop"] = relationship("Stop", backref="stop_times")

    __table_args__ = (UniqueConstraint("trip_id", "stop_id", name="uq_trip_stop"),)