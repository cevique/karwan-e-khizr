from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)
    distance_along_route_m: Mapped[float | None] = mapped_column(nullable=True)

    route: Mapped["Route"] = relationship("Route", backref="route_stops")
    stop: Mapped["Stop"] = relationship("Stop", backref="route_stops")

    __table_args__ = (UniqueConstraint("route_id", "stop_id", name="uq_route_stop"),)