import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.policy import CoveragePlanType
from app.models.premium import PremiumPaymentStatus


class PremiumBase(BaseModel):
    policy_id: uuid.UUID | None = None
    worker_id: uuid.UUID | None = None
    week_start: date | None = None
    week_end: date | None = None
    zone_risk: Decimal | None = None
    exposure_score: Decimal | None = None
    income_loss_rate: Decimal | None = None
    weekly_income: Decimal | None = None
    expected_loss: Decimal | None = None
    uncertainty_buffer: Decimal | None = None
    operating_margin: Decimal | None = None
    catastrophe_loading: Decimal | None = None
    plan_multiplier: Decimal | None = None
    final_premium: Decimal | None = None
    payment_status: PremiumPaymentStatus | None = PremiumPaymentStatus.pending
    payment_ref: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_week_range(self) -> "PremiumBase":
        if self.week_start and self.week_end and self.week_end < self.week_start:
            raise ValueError("week_end cannot be before week_start")
        return self


class PremiumCreate(PremiumBase):
    pass


class PremiumCalculationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "d53cf46d-c871-4ca6-ae4d-f9edc91decea",
                "coverage_plan": "standard",
            }
        }
    )

    worker_id: uuid.UUID
    coverage_plan: CoveragePlanType


class PremiumBreakdownResponse(BaseModel):
    zone_risk: Decimal
    exposure_score: Decimal
    income_loss_rate: Decimal
    weekly_income: Decimal
    expected_loss: Decimal
    uncertainty_buffer: Decimal
    operating_margin: Decimal
    catastrophe_loading: Decimal
    plan_multiplier: Decimal
    final_premium: Decimal


class PremiumCalculationResponse(BaseModel):
    worker_id: uuid.UUID
    coverage_plan: CoveragePlanType
    breakdown: PremiumBreakdownResponse
    plan_comparison: dict[CoveragePlanType, Decimal]


class PremiumHistoryResponse(BaseModel):
    worker_id: uuid.UUID
    records: list["PremiumRead"]


class PremiumUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_status: PremiumPaymentStatus | None = None
    payment_ref: str | None = Field(default=None, max_length=100)
    paid_at: datetime | None = None


class PremiumRead(PremiumBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    paid_at: datetime | None


PremiumHistoryResponse.model_rebuild()
