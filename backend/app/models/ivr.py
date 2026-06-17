import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IvrCall(Base):
    __tablename__ = "ivr_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="en")
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    call_status: Mapped[str] = mapped_column(String(20), default="queued")
    call_sid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
