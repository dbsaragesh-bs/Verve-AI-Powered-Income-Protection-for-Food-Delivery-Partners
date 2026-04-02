import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CoveragePlanType(str, enum.Enum):
    basic = "basic"
    standard = "standard"
    complete = "complete"


class PolicyStatus(str, enum.Enum):
    created = "created"
    active = "active"
    renewal_due = "renewal_due"
    renewed = "renewed"
    lapsed = "lapsed"
    cancelled = "cancelled"


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False
    )
    coverage_plan: Mapped[CoveragePlanType] = mapped_column(
        Enum(CoveragePlanType, name="coverage_plan_type"), nullable=False
    )
    coverage_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    coverage_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    weekly_premium: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    premium_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payment_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    covered_disruptions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    max_per_event: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    copay_rate: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus, name="policy_status"), nullable=False
    )
    previous_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id"), nullable=True
    )
    renewal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    worker: Mapped["Worker"] = relationship("Worker", back_populates="policies")
    previous_policy: Mapped["Policy | None"] = relationship("Policy", remote_side=[id])
    claims: Mapped[list["Claim"]] = relationship("Claim", back_populates="policy")
    premiums: Mapped[list["Premium"]] = relationship("Premium", back_populates="policy")
