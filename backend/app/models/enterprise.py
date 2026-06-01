import hashlib
import os
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _generate_api_key() -> str:
    return "uk_" + hashlib.sha256(os.urandom(32)).hexdigest()[:48]


def _generate_webhook_secret() -> str:
    return "whsec_" + hashlib.sha256(os.urandom(32)).hexdigest()[:40]


class UtilityCompany(Base):
    __tablename__ = "utility_companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(5), nullable=False)
    service_area_h3_cells: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list of H3 indices
    api_key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, default=_generate_api_key)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[str] = mapped_column(String(20), default="trial")  # trial | pro | enterprise
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False)  # shop|restaurant|office|factory|hospital|other
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Monthly revenue estimate in USD (used to compute impact cost)
    monthly_revenue_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(String(60), nullable=False, default=_generate_webhook_secret)
    threshold_probability: Mapped[float] = mapped_column(Float, default=0.70)
    events: Mapped[list] = mapped_column(JSONB, default=["prediction_threshold", "outage_confirmed"])
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
