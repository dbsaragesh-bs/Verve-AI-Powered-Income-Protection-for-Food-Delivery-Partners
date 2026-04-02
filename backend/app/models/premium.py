import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PremiumPaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class Premium(Base):
    __tablename__ = "premiums"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id"), nullable=True
    )
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )
    week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    week_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    zone_risk: Mapped[Decimal | None] = mapped_column(Numeric(5, 3), nullable=True)
    exposure_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 3), nullable=True)
    income_loss_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3), nullable=True
    )
    weekly_income: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    expected_loss: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    uncertainty_buffer: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    operating_margin: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    catastrophe_loading: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    plan_multiplier: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    final_premium: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    payment_status: Mapped[PremiumPaymentStatus | None] = mapped_column(
        Enum(PremiumPaymentStatus, name="premium_payment_status"), nullable=True
    )
    payment_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    policy: Mapped["Policy | None"] = relationship("Policy", back_populates="premiums")
    worker: Mapped["Worker | None"] = relationship("Worker", back_populates="premiums")
