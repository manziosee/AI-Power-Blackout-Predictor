import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WhatsAppSubscription(Base):
    __tablename__ = "whatsapp_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    opted_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TelegramSubscription(Base):
    __tablename__ = "telegram_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    chat_id: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    h3_index: Mapped[str | None] = mapped_column(String(15), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailSubscription(Base):
    __tablename__ = "email_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_digest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
