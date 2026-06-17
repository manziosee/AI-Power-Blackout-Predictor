import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PrepaidMeter(Base):
    __tablename__ = "prepaid_meters"
    __table_args__ = (UniqueConstraint("user_id", "meter_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meter_number: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False)
    last_balance_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_balance_threshold_kwh: Mapped[float] = mapped_column(Float, default=10.0)
    alert_before_hours: Mapped[int] = mapped_column(Integer, default=12, server_default="12")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PrepaidTopupReminder(Base):
    __tablename__ = "prepaid_topup_reminders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    meter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prepaid_meters.id", ondelete="CASCADE"), nullable=False
    )
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    message_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    balance_at_send: Mapped[float | None] = mapped_column(Float, nullable=True)
    topup_detected: Mapped[bool] = mapped_column(Boolean, default=False)
