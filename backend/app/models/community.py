import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPoints(Base):
    __tablename__ = "user_points"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    weekly_points: Mapped[int] = mapped_column(Integer, default=0)
    monthly_points: Mapped[int] = mapped_column(Integer, default=0)
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    confirm_count: Mapped[int] = mapped_column(Integer, default=0)
    note_count: Mapped[int] = mapped_column(Integer, default=0)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    badge_key: Mapped[str] = mapped_column(String(50), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    badge_emoji: Mapped[str] = mapped_column(String(10), nullable=False)
    badge_description: Mapped[str] = mapped_column(String(200), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)   # report | confirm | first_report | note | streak
    reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # outage_report id etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunityNote(Base):
    __tablename__ = "community_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    body: Mapped[str] = mapped_column(String(280), nullable=False)
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NoteUpvote(Base):
    __tablename__ = "note_upvotes"
    __table_args__ = (UniqueConstraint("note_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NeighborAlertLog(Base):
    __tablename__ = "neighbor_alert_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    triggered_by_report_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    recipients_count: Mapped[int] = mapped_column(Integer, default=0)
