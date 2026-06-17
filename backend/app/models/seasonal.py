import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SeasonalStats(Base):
    __tablename__ = "seasonal_stats"
    __table_args__ = (UniqueConstraint("h3_index", "month", "year"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    outage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_outage_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
