from decimal import Decimal

from pydantic import BaseModel


class DashboardKPI(BaseModel):
    total_workers: int
    active_policies: int
    pending_claims: int
    total_payout: Decimal


class WorkerMobileDashboard(BaseModel):
    worker_id: str
    active_policy: bool
    recent_claim_status: str | None
    upcoming_premium: Decimal | None
