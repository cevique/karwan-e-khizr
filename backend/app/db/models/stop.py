from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from geoalchemy2 import Geometry


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Geometry | None] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    coordinate_source: Mapped[str | None] = mapped_column(SQLEnum("nominatim", "curated", "UNKNOWN", name="coordinate_source_enum"), nullable=True)
    coordinate_confidence: Mapped[str | None] = mapped_column(SQLEnum("HIGH", "APPROXIMATE", "UNKNOWN", name="coordinate_confidence_enum"), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(50), nullable=True)