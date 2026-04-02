import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payout import PayoutStatus, PayoutType


class PayoutBase(BaseModel):
    claim_id: uuid.UUID | None = None
    worker_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0)
    payout_type: PayoutType | None = PayoutType.full
    payment_method: str = Field(default="upi", max_length=20)
    upi_id: str | None = Field(default=None, max_length=50)
    razorpay_payout_id: str | None = Field(default=None, max_length=100)
    status: PayoutStatus | None = PayoutStatus.initiated


class PayoutCreate(PayoutBase):
    pass


class PayoutUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: PayoutStatus | None = None
    razorpay_payout_id: str | None = Field(default=None, max_length=100)
    completed_at: datetime | None = None


class PayoutRead(PayoutBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    completed_at: datetime | None
