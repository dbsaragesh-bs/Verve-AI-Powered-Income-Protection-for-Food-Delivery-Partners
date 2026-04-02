import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.policy import CoveragePlanType, PolicyStatus


class PolicyBase(BaseModel):
    worker_id: uuid.UUID
    coverage_plan: CoveragePlanType


class PolicyCreate(PolicyBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "f95ff971-7b15-40e7-9dfd-350cefc229cc",
                "coverage_plan": "standard",
            }
        }
    )


class PolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_ref: str | None = Field(default=None, max_length=100)


class PremiumBreakdown(BaseModel):
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


class PolicyResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "policy_id": "f95ff971-7b15-40e7-9dfd-350cefc229cc",
                "worker_id": "d53cf46d-c871-4ca6-ae4d-f9edc91decea",
                "coverage_plan": "standard",
                "weekly_premium": 149,
                "premium_breakdown": {
                    "zone_risk": 0.35,
                    "exposure_score": 0.72,
                    "income_loss_rate": 0.18,
                    "weekly_income": 5500,
                    "expected_loss": 249.5,
                    "uncertainty_buffer": 1.35,
                    "operating_margin": 15.0,
                    "catastrophe_loading": 8.0,
                    "plan_multiplier": 1.0,
                    "final_premium": 149,
                },
                "coverage_start": "2024-07-15T00:00:00+05:30",
                "coverage_end": "2024-07-21T23:59:59+05:30",
                "covered_disruptions": [
                    "HEAVY_RAINFALL",
                    "FLOODING",
                    "EXTREME_HEAT",
                    "SEVERE_AQI",
                    "TRANSPORT_STRIKE",
                    "CURFEW",
                ],
                "max_per_event_payout": 800,
                "copay_rate": 0.25,
                "status": "created",
            }
        }
    )

    policy_id: uuid.UUID
    worker_id: uuid.UUID
    coverage_plan: CoveragePlanType
    weekly_premium: Decimal
    premium_breakdown: PremiumBreakdown
    coverage_start: datetime
    coverage_end: datetime
    covered_disruptions: list[str]
    max_per_event_payout: Decimal
    copay_rate: Decimal
    status: PolicyStatus


class PolicyRead(PolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    coverage_start: datetime
    coverage_end: datetime
    weekly_premium: Decimal
    premium_paid: bool
    payment_ref: str | None
    covered_disruptions: list[str]
    max_per_event: Decimal
    copay_rate: Decimal
    status: PolicyStatus
    previous_policy_id: uuid.UUID | None
    renewal_count: int
    created_at: datetime
    updated_at: datetime
