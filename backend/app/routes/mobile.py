import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.claim import Claim, ClaimDecision, ClaimStatus
from app.models.event import Event
from app.models.payout import Payout, PayoutStatus
from app.models.policy import CoveragePlanType, Policy, PolicyStatus
from app.models.premium import Premium
from app.models.worker import PlatformType, WorkPatternType, Worker
from app.schemas.policy import PolicyCreate
from app.schemas.worker import WorkerCreate
from app.services.policy_service import PolicyService
from app.services.premium_service import PremiumService
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/mobile", tags=["mobile"])

EVENT_ICON = {
    "HEAVY_RAINFALL": "🌧️",
    "EXTREME_HEAT": "🌡️",
    "SEVERE_AQI": "💨",
    "TRANSPORT_STRIKE": "🚫",
    "FLOODING": "🌊",
    "PLATFORM_OUTAGE": "📱",
    "CURFEW": "🔒",
}


class MobileRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    platform: PlatformType
    partner_id: str | None = None
    city: str = "bengaluru"
    primary_zones: list[str] = Field(min_length=1)
    work_pattern: WorkPatternType
    typical_hours: list[str] | None = None
    upi_id: str | None = None
    coverage_plan: CoveragePlanType


@router.post("/register")
async def mobile_register(
    payload: MobileRegisterRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Register worker, create policy, and auto-activate for demo flow."""
    worker_payload = WorkerCreate(
        name=payload.name,
        phone=payload.phone,
        platform=payload.platform,
        partner_id=payload.partner_id,
        city=payload.city,
        primary_zones=payload.primary_zones,
        work_pattern=payload.work_pattern,
        typical_hours=payload.typical_hours,
        upi_id=payload.upi_id,
    )
    worker = await RegistrationService.create_worker(db, worker_payload)

    policy_input = PolicyCreate(
        worker_id=worker.id, coverage_plan=payload.coverage_plan
    )
    policy, premium = await PolicyService.create_policy(db, policy_input)
    policy = await PolicyService.activate_policy(db, policy)

    return {
        "worker": {
            "worker_id": str(worker.id),
            "name": worker.name,
            "phone": worker.phone,
            "platform": worker.platform.value,
            "trust_score": float(worker.trust_score),
        },
        "policy": {
            "policy_id": str(policy.id),
            "plan": policy.coverage_plan.value,
            "status": policy.status.value,
            "premium": float(policy.weekly_premium),
            "coverage_start": policy.coverage_start,
            "coverage_end": policy.coverage_end,
            "covered_disruptions": policy.covered_disruptions,
            "max_per_event": float(policy.max_per_event),
            "copay_rate": float(policy.copay_rate),
        },
        "premium": {
            "zone_risk": float(premium.zone_risk or 0),
            "final_premium": float(premium.final_premium or 0),
            "payment_status": premium.payment_status.value
            if premium.payment_status
            else None,
        },
    }


@router.get("/home/{worker_id}")
async def mobile_home(
    worker_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return complete mobile home dashboard payload for a worker."""
    worker = await db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="worker not found"
        )

    policy = await db.scalar(
        select(Policy)
        .where(Policy.worker_id == worker_id, Policy.status == PolicyStatus.active)
        .order_by(Policy.created_at.desc())
    )

    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    week_claims = list(
        (
            await db.execute(
                select(Claim).where(
                    Claim.worker_id == worker_id,
                    Claim.created_at >= week_start,
                    Claim.created_at < week_end,
                )
            )
        )
        .scalars()
        .all()
    )

    disruption_loss = sum(
        [
            Decimal(c.causal_gap or 0)
            for c in week_claims
            if c.decision == ClaimDecision.approved
        ],
        Decimal("0"),
    )
    verve_recovered = sum(
        [
            Decimal(c.final_payout or 0)
            for c in week_claims
            if c.status == ClaimStatus.paid
        ],
        Decimal("0"),
    )
    protection_rate = float(
        (verve_recovered / disruption_loss) if disruption_loss > 0 else Decimal("1")
    )

    total_earned = sum(
        [Decimal(c.actual_income or 0) for c in week_claims], Decimal("0")
    )
    if total_earned <= 0:
        total_earned = Decimal(worker.weekly_avg_income)

    active_events = list(
        (
            await db.execute(
                select(Event).where(
                    Event.lifecycle_phase.in_(["onset", "active", "peak"])
                )
            )
        )
        .scalars()
        .all()
    )

    redis_client = getattr(request.app.state, "redis", None)
    zone_risk = []
    for zone in worker.primary_zones:
        meta = PremiumService.ZONES_META.get(
            zone, {"name": zone, "base_risk": Decimal("0.25")}
        )
        risk = Decimal(meta["base_risk"])
        if redis_client is not None:
            cached = await redis_client.get(f"zone:risk:{zone}")
            if cached is not None:
                risk = Decimal(str(cached))

        alert = None
        for event in active_events:
            if zone in (event.affected_zones or []):
                alert = f"{event.event_type} ({event.severity})"
                break

        zone_risk.append(
            {"name": str(meta["name"]), "h3": zone, "risk": float(risk), "alert": alert}
        )

    payout_rows = (
        await db.execute(
            select(Payout, Claim, Event.event_type)
            .join(Claim, Payout.claim_id == Claim.id)
            .join(Event, Claim.event_id == Event.id)
            .where(Payout.worker_id == worker_id)
            .order_by(Payout.created_at.desc())
            .limit(5)
        )
    ).all()
    recent_payouts = [
        {
            "date": payout.created_at,
            "event_type": event_type,
            "amount": float(payout.amount),
            "status": payout.status.value if payout.status else None,
            "explanation": claim.decision_reasoning,
            "event_icon": EVENT_ICON.get(event_type, "💸"),
        }
        for payout, claim, event_type in payout_rows
    ]

    next_premium_amount = Decimal(policy.weekly_premium) if policy else Decimal("0")
    change = Decimal("0")
    reason = "New enrollment" if policy else "No active coverage"

    return {
        "worker": {
            "name": worker.name,
            "trust_score": float(worker.trust_score),
            "adaptation_score": float(worker.adaptation_score),
        },
        "coverage": {
            "status": policy.status.value if policy else "none",
            "plan": policy.coverage_plan.value if policy else None,
            "premium": float(policy.weekly_premium) if policy else 0,
            "coverage_end": policy.coverage_end if policy else None,
            "max_per_event": float(policy.max_per_event) if policy else 0,
        },
        "this_week": {
            "total_earned": float(total_earned),
            "disruption_loss": float(disruption_loss),
            "verve_recovered": float(verve_recovered),
            "protection_rate": protection_rate,
            "claims_count": len(week_claims),
        },
        "zone_risk": zone_risk,
        "recent_payouts": recent_payouts,
        "next_premium": {
            "amount": float(next_premium_amount),
            "change": float(change),
            "reason": reason,
        },
    }


@router.get("/coverage/{worker_id}")
async def mobile_coverage(
    worker_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return coverage, premium history, and current-week claim/payout metrics."""
    worker = await db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="worker not found"
        )

    policy = await db.scalar(
        select(Policy)
        .where(Policy.worker_id == worker_id, Policy.status == PolicyStatus.active)
        .order_by(Policy.created_at.desc())
    )
    premium_history = list(
        (
            await db.execute(
                select(Premium)
                .where(Premium.worker_id == worker_id)
                .order_by(Premium.created_at.desc())
                .limit(12)
            )
        )
        .scalars()
        .all()
    )

    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    claims_this_week = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.worker_id == worker_id,
                Claim.created_at >= week_start,
                Claim.created_at < week_end,
            )
        )
        or 0
    )
    total_payout_this_week = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Payout.amount), Decimal("0"))).where(
                Payout.worker_id == worker_id,
                Payout.status == PayoutStatus.completed,
                Payout.created_at >= week_start,
                Payout.created_at < week_end,
            )
        )
        or 0
    )

    max_per_event = Decimal(policy.max_per_event) if policy else Decimal("0")
    max_remaining = max(Decimal("0"), max_per_event - total_payout_this_week)

    return {
        "current_policy": {
            "policy_id": str(policy.id),
            "plan": policy.coverage_plan.value,
            "status": policy.status.value,
            "coverage_start": policy.coverage_start,
            "coverage_end": policy.coverage_end,
            "premium": float(policy.weekly_premium),
            "max_per_event": float(policy.max_per_event),
            "copay_rate": float(policy.copay_rate),
        }
        if policy
        else None,
        "premium_history": [
            {
                "premium_id": str(item.id),
                "week_start": item.week_start,
                "week_end": item.week_end,
                "final_premium": float(item.final_premium or 0),
                "payment_status": item.payment_status.value
                if item.payment_status
                else None,
                "zone_risk": float(item.zone_risk or 0),
            }
            for item in premium_history
        ],
        "covered_events": policy.covered_disruptions if policy else [],
        "excluded_events": ["HEALTH", "LIFE", "ACCIDENTS", "VEHICLE_REPAIR"],
        "claims_this_week": claims_this_week,
        "total_payout_this_week": float(total_payout_this_week),
        "max_remaining_this_week": float(max_remaining),
    }


@router.get("/payouts/{worker_id}")
async def mobile_payouts(
    worker_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return payout ledger with event attribution and aggregate totals."""
    worker = await db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="worker not found"
        )

    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)

    total_received_alltime = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Payout.amount), Decimal("0"))).where(
                Payout.worker_id == worker_id,
                Payout.status == PayoutStatus.completed,
            )
        )
        or 0
    )
    total_received_this_month = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Payout.amount), Decimal("0"))).where(
                Payout.worker_id == worker_id,
                Payout.status == PayoutStatus.completed,
                Payout.created_at >= month_start,
            )
        )
        or 0
    )

    payout_rows = (
        await db.execute(
            select(Payout, Claim, Event.event_type)
            .join(Claim, Claim.id == Payout.claim_id)
            .join(Event, Claim.event_id == Event.id)
            .where(Payout.worker_id == worker_id)
            .order_by(Payout.created_at.desc())
        )
    ).all()

    payouts = [
        {
            "payout_id": str(payout.id),
            "date": payout.created_at,
            "event_type": event_type,
            "event_icon": EVENT_ICON.get(event_type, "💸"),
            "expected_income": float(claim.expected_income or 0),
            "actual_income": float(claim.actual_income or 0),
            "causal_gap": float(claim.causal_gap or 0),
            "payout_amount": float(payout.amount),
            "payout_type": payout.payout_type.value if payout.payout_type else None,
            "status": payout.status.value if payout.status else None,
            "explanation": claim.decision_reasoning,
        }
        for payout, claim, event_type in payout_rows
    ]

    return {
        "total_received_alltime": float(total_received_alltime),
        "total_received_this_month": float(total_received_this_month),
        "payouts": payouts,
    }
