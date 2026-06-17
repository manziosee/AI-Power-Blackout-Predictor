import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RegulatoryReport(Base):
    __tablename__ = "regulatory_reports"
    __table_args__ = (UniqueConstraint("country_code", "district", "report_year", "report_month"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    report_year: Mapped[int] = mapped_column(Integer, nullable=False)
    report_month: Mapped[int] = mapped_column(Integer, nullable=False)
    total_outages: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_outage_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    uptime_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    affected_cells_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    worst_cell_h3: Mapped[str | None] = mapped_column(String(15), nullable=True)
    avg_repair_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class DispatchRecommendation(Base):
    __tablename__ = "dispatch_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utility_companies.id", ondelete="SET NULL"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    high_risk_cells: Mapped[list] = mapped_column(JSONB, nullable=False)
    recommended_positions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    crew_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    total_priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
