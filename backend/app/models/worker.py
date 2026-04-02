import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlatformType(str, enum.Enum):
    swiggy = "swiggy"
    zomato = "zomato"


class WorkPatternType(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    weekends = "weekends"


class WorkerStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    platform: Mapped[PlatformType] = mapped_column(
        Enum(PlatformType, name="platform_type"), nullable=False
    )
    partner_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str] = mapped_column(String(50), nullable=False, default="bengaluru")
    primary_zones: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    work_pattern: Mapped[WorkPatternType] = mapped_column(
        Enum(WorkPatternType, name="work_pattern_type"), nullable=False
    )
    typical_hours: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    weekly_avg_income: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    trust_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.70")
    )
    adaptation_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.50")
    )
    upi_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status"),
        nullable=False,
        default=WorkerStatus.active,
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

    policies: Mapped[list["Policy"]] = relationship("Policy", back_populates="worker")
    claims: Mapped[list["Claim"]] = relationship("Claim", back_populates="worker")
    premiums: Mapped[list["Premium"]] = relationship("Premium", back_populates="worker")
    payouts: Mapped[list["Payout"]] = relationship("Payout", back_populates="worker")
