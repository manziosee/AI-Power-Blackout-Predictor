import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RegionSimilarity(Base):
    __tablename__ = "region_similarities"
    __table_args__ = (UniqueConstraint("source_region", "target_region"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    basis: Mapped[str] = mapped_column(String(50), default="climate")
    climate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    infrastructure_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
