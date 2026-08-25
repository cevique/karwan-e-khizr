from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from geoalchemy2 import Geometry


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), nullable=False)
    short_name: Mapped[str] = mapped_column(String(100), nullable=False)
    long_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    route_type: Mapped[str] = mapped_column(SQLEnum("bus", "metro", "feeder", name="route_type_enum"), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    text_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    path: Mapped[Geometry | None] = mapped_column(Geometry("LINESTRING", srid=4326), nullable=True)
    geometry_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    geometry_confidence: Mapped[str | None] = mapped_column(SQLEnum("HIGH", "APPROXIMATE", name="geometry_confidence_enum"), nullable=True)

    agency: Mapped["Agency"] = relationship("Agency", backref="routes")