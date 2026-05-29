from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class H3Cell(Base):
    __tablename__ = "h3_cells"

    h3_index: Mapped[str] = mapped_column(String(15), primary_key=True)
    center_lat: Mapped[float | None] = mapped_column(Float)
    center_lng: Mapped[float | None] = mapped_column(Float)
    country_code: Mapped[str | None] = mapped_column(String(5))
    region: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    resolution: Mapped[int] = mapped_column(Integer, default=8)
