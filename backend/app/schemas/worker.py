import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.policy import CoveragePlanType, PolicyStatus
from app.models.worker import PlatformType, WorkerStatus, WorkPatternType


class WorkerBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    platform: PlatformType
    partner_id: str | None = Field(default=None, max_length=50)
    city: str = Field(default="bengaluru", max_length=50)
    primary_zones: list[str] = Field(min_length=1)
    work_pattern: WorkPatternType
    typical_hours: list[str] | None = None
    upi_id: str | None = Field(default=None, max_length=50)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not value.lstrip("+").isdigit():
            raise ValueError("phone must contain only digits and optional +")
        return value


class WorkerCreate(WorkerBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Ravi Kumar",
                "phone": "9876543210",
                "platform": "zomato",
                "partner_id": "ZOM_12345",
                "city": "bengaluru",
                "primary_zones": ["8928308280fffff", "8928308281fffff"],
                "work_pattern": "full_time",
                "typical_hours": ["morning", "afternoon", "evening"],
                "upi_id": "ravi@upi",
            }
        }
    )


class SuggestedPremiums(BaseModel):
    basic: Decimal
    standard: Decimal
    complete: Decimal


class WorkerRegistrationResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "f95ff971-7b15-40e7-9dfd-350cefc229cc",
                "name": "Ravi Kumar",
                "platform": "zomato",
                "city": "bengaluru",
                "primary_zones": ["8928308280fffff", "8928308281fffff"],
                "work_pattern": "full_time",
                "cluster_id": 1,
                "weekly_avg_income": 5500,
                "trust_score": 0.7,
                "status": "active",
                "suggested_premiums": {"basic": 89, "standard": 149, "complete": 219},
            }
        }
    )

    worker_id: uuid.UUID
    name: str
    platform: PlatformType
    city: str
    primary_zones: list[str]
    work_pattern: WorkPatternType
    cluster_id: int
    weekly_avg_income: Decimal
    trust_score: Decimal
    status: WorkerStatus
    suggested_premiums: SuggestedPremiums


class ActivePolicySummary(BaseModel):
    policy_id: uuid.UUID
    coverage_plan: CoveragePlanType
    weekly_premium: Decimal
    coverage_start: datetime
    coverage_end: datetime
    status: PolicyStatus


class WorkerProfileResponse(BaseModel):
    worker_id: uuid.UUID
    name: str
    phone: str
    platform: PlatformType
    partner_id: str | None
    city: str
    primary_zones: list[str]
    work_pattern: WorkPatternType
    typical_hours: list[str] | None
    weekly_avg_income: Decimal
    trust_score: Decimal
    adaptation_score: Decimal
    upi_id: str | None
    cluster_id: int | None
    data_weeks: int
    status: WorkerStatus
    created_at: datetime
    updated_at: datetime
    active_policy: ActivePolicySummary | None = None


class WorkerListItem(BaseModel):
    worker_id: uuid.UUID
    name: str
    platform: PlatformType
    city: str
    work_pattern: WorkPatternType
    cluster_id: int | None
    weekly_avg_income: Decimal
    status: WorkerStatus


class WorkerListResponse(BaseModel):
    page: int
    limit: int
    total: int
    items: list[WorkerListItem]


class WorkerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    city: str | None = Field(default=None, max_length=50)
    primary_zones: list[str] | None = None
    typical_hours: list[str] | None = None
    weekly_avg_income: Decimal | None = None
    trust_score: Decimal | None = None
    adaptation_score: Decimal | None = None
    upi_id: str | None = Field(default=None, max_length=50)
    cluster_id: int | None = None
    data_weeks: int | None = None
    status: WorkerStatus | None = None


class WorkerRead(WorkerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    weekly_avg_income: Decimal
    trust_score: Decimal
    adaptation_score: Decimal
    cluster_id: int | None
    data_weeks: int
    status: WorkerStatus
    created_at: datetime
    updated_at: datetime
