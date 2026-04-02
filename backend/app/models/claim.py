import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FraudTier(str, enum.Enum):
    green = "green"
    amber = "amber"
    red = "red"


class ClaimDecision(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    held = "held"
    pending = "pending"


class ClaimStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    paid = "paid"
    rejected = "rejected"
    under_review = "under_review"
    provisional_paid = "provisional_paid"


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False
    )
    compound_event_id: Mapped[str] = mapped_column(String(50), nullable=False)
    expected_income: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    actual_income: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    raw_gap: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    causal_fraction: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    causal_gap: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    drop_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    payout_fraction: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    coverage_rate: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    calculated_payout: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    final_payout: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    fraud_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 3), nullable=True)
    fraud_flags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    fraud_tier: Mapped[FraudTier | None] = mapped_column(
        Enum(FraudTier, name="fraud_tier"), nullable=True
    )
    decision: Mapped[ClaimDecision | None] = mapped_column(
        Enum(ClaimDecision, name="claim_decision"), nullable=True
    )
    decision_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    status: Mapped[ClaimStatus | None] = mapped_column(
        Enum(ClaimStatus, name="claim_status"), nullable=True
    )
    provisional_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    policy: Mapped["Policy"] = relationship("Policy", back_populates="claims")
    worker: Mapped["Worker"] = relationship("Worker", back_populates="claims")
    event: Mapped["Event"] = relationship("Event", back_populates="claims")
    payouts: Mapped[list["Payout"]] = relationship("Payout", back_populates="claim")
