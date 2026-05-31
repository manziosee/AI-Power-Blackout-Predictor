import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    region_model: Mapped[str] = mapped_column(String(50), nullable=False)
    features_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Duration prediction (minutes)
    predicted_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predicted_duration_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predicted_duration_median: Mapped[int | None] = mapped_column(Integer, nullable=True)
