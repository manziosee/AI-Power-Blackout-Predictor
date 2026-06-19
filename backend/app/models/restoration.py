import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_VALID_STATUSES = ("reported", "acknowledged", "crew_assigned", "crew_en_route", "crew_on_site", "restored", "cancelled")


class RestorationEvent(Base):
    __tablename__ = "restoration_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outage_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outage_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    utility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utility_companies.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="reported", nullable=False)
    eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crew_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crew_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
