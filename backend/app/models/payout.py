import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PayoutType(str, enum.Enum):
    full = "full"
    provisional = "provisional"


class PayoutStatus(str, enum.Enum):
    initiated = "initiated"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True
    )
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payout_type: Mapped[PayoutType | None] = mapped_column(
        Enum(PayoutType, name="payout_type"), nullable=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="upi"
    )
    upi_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    razorpay_payout_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[PayoutStatus | None] = mapped_column(
        Enum(PayoutStatus, name="payout_status"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    claim: Mapped["Claim | None"] = relationship("Claim", back_populates="payouts")
    worker: Mapped["Worker | None"] = relationship("Worker", back_populates="payouts")
