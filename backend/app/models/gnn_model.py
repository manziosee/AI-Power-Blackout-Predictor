import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GnnPrediction(Base):
    __tablename__ = "gnn_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    transformer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("grid_transformers.id", ondelete="SET NULL"), nullable=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    cascade_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    affected_cells: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str] = mapped_column(String(20), default="gnn_v0", server_default="gnn_v0")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
