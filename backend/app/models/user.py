from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Time, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.alert import AlertSubscription, SmsAlert


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    country_code: Mapped[str] = mapped_column(String(5), nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="en")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    locations: Mapped[list["UserLocation"]] = relationship("UserLocation", back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[list["AlertSubscription"]] = relationship("AlertSubscription", back_populates="user", cascade="all, delete-orphan")
    sms_alerts: Mapped[list["SmsAlert"]] = relationship("SmsAlert", back_populates="user")


class UserLocation(Base):
    __tablename__ = "user_locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False)
    label: Mapped[str | None] = mapped_column(String(50))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_threshold: Mapped[float] = mapped_column(Float, default=0.70)
    quiet_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    notify_channels: Mapped[list] = mapped_column(JSONB, default=["sms", "push"])
    location_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # home/office/family/other
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="locations")
