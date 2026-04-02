import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.claim import ClaimDecision, ClaimStatus, FraudTier


class ClaimBase(BaseModel):
    policy_id: uuid.UUID
    worker_id: uuid.UUID
    event_id: uuid.UUID
    compound_event_id: str = Field(min_length=3, max_length=50)
    expected_income: Decimal | None = None
    actual_income: Decimal | None = None
    raw_gap: Decimal | None = None
    causal_fraction: Decimal | None = Field(default=None, ge=0, le=1)
    causal_gap: Decimal | None = None
    drop_ratio: Decimal | None = Field(default=None, ge=0, le=1)
    payout_fraction: Decimal | None = Field(default=None, ge=0, le=1)
    coverage_rate: Decimal | None = Field(default=None, ge=0, le=1)
    calculated_payout: Decimal | None = None
    final_payout: Decimal | None = None
    fraud_score: Decimal | None = Field(default=None, ge=0, le=1)
    fraud_flags: list[str] | None = None
    fraud_tier: FraudTier | None = None
    decision: ClaimDecision | None = None
    decision_reasoning: str | None = None
    decision_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    status: ClaimStatus | None = ClaimStatus.pending
    provisional_amount: Decimal | None = None


class ClaimCreate(ClaimBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "policy_id": "f95ff971-7b15-40e7-9dfd-350cefc229cc",
                "worker_id": "d53cf46d-c871-4ca6-ae4d-f9edc91decea",
                "event_id": "39f15514-32a3-47e1-8891-a306f8a897f0",
                "compound_event_id": "EVT_2024_BLR_0001",
            }
        }
    )


class ClaimUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ClaimDecision | None = None
    decision_reasoning: str | None = None
    decision_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    status: ClaimStatus | None = None
    final_payout: Decimal | None = None
    provisional_amount: Decimal | None = None
    paid_at: datetime | None = None


class ClaimRead(ClaimBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    decided_at: datetime | None
    paid_at: datetime | None


class ClaimTriggerEvaluationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"event_id": "39f15514-32a3-47e1-8891-a306f8a897f0"},
                {"scenario": "afternoon_thunderstorm"},
            ]
        }
    )

    event_id: uuid.UUID | None = None
    scenario: str | None = None


class ClaimReviewRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision": "approve",
                "reviewer_notes": "Validated with partner platform logs",
            }
        }
    )

    decision: str = Field(pattern="^(approve|reject)$")
    reviewer_notes: str | None = None


class ClaimPipelineSummary(BaseModel):
    event_id: str
    compound_event_id: str
    event_type: str
    workers_evaluated: int
    claims_created: int
    claims_approved: int
    claims_held: int
    claims_rejected: int
    total_payout: Decimal
    skipped_no_policy: int


class ClaimListResponse(BaseModel):
    page: int
    limit: int
    total: int
    items: list[ClaimRead]
