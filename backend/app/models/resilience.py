import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResilienceScore(Base):
    __tablename__ = "resilience_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    outage_frequency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_duration_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_participation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    outages_30d: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
