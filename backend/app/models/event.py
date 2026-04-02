import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    compound_event_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    affected_zones: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    signal_sources: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    onset_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    peak_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    recovery_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    lifecycle_phase: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weather_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    traffic_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    platform_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    social_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    claims_triggered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_payout: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    claims: Mapped[list["Claim"]] = relationship("Claim", back_populates="event")
