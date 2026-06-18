import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GridLoadSnapshot(Base):
    __tablename__ = "grid_load_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # entso-e / eia / manual
    load_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    load_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
