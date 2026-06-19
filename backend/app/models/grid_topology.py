import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GridTransformer(Base):
    __tablename__ = "grid_transformers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    transformer_type: Mapped[str] = mapped_column(String(30), default="distribution")
    lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    h3_index: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    capacity_kva: Mapped[float | None] = mapped_column(Float, nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    utility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utility_companies.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_maintenance_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    maintenance_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_count_90d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransformerCellCoverage(Base):
    __tablename__ = "transformer_cell_coverage"
    __table_args__ = (UniqueConstraint("transformer_id", "h3_index"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transformer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grid_transformers.id", ondelete="CASCADE"), nullable=False
    )
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
