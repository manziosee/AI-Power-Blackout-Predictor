import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PredictionAccuracy(Base):
    __tablename__ = "prediction_accuracy"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    true_positives: Mapped[int] = mapped_column(Integer, default=0)
    false_positives: Mapped[int] = mapped_column(Integer, default=0)
    true_negatives: Mapped[int] = mapped_column(Integer, default=0)
    false_negatives: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NeighborhoodStats(Base):
    __tablename__ = "neighborhood_stats"

    h3_index: Mapped[str] = mapped_column(String(15), primary_key=True)
    country_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outages_7d: Mapped[int] = mapped_column(Integer, default=0)
    outages_30d: Mapped[int] = mapped_column(Integer, default=0)
    outages_90d: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_probability_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank_country: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_city: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
