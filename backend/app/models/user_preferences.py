import uuid
from datetime import time

from sqlalchemy import Boolean, Float, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserNotificationPreferences(Base):
    """Global per-user notification preferences (not per-cell)."""
    __tablename__ = "user_notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    # Which channels are globally enabled
    channels: Mapped[list] = mapped_column(JSONB, default=["sms", "push"])
    # Global probability threshold (overridden per-subscription if set)
    default_threshold: Mapped[float] = mapped_column(Float, default=0.70)
    # Global quiet hours
    quiet_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    # Minimum risk level to always break quiet hours
    quiet_risk_override: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Master kill-switch
    all_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User")  # noqa: F821
