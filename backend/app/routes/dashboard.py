import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.claim import Claim, ClaimStatus, FraudTier
from app.models.event import Event
from app.models.payout import Payout, PayoutStatus
from app.models.policy import Policy, PolicyStatus
from app.models.premium import Premium, PremiumPaymentStatus
from app.models.worker import Worker, WorkerStatus
from app.services.premium_service import PremiumService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

ZONE_COORDS = {
    "8928308280fffff": (12.9352, 77.6245),
    "8928308281fffff": (12.9719, 77.6412),
    "8928308282fffff": (12.9116, 77.6474),
    "8928308283fffff": (12.9698, 77.7499),
    "8928308284fffff": (12.9784, 77.5720),
    "8928308285fffff": (12.8399, 77.6770),
    "8928308286fffff": (12.9591, 77.6974),
    "8928308287fffff": (12.9250, 77.5938),
    "8928308288fffff": (12.9756, 77.6050),
    "8928308289fffff": (12.9635, 77.5713),
}


def _day_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)
    return start, end


@router.get("/metrics")
async def dashboard_metrics(db: AsyncSession = Depends(get_db)) -> dict:
    """Return top-level portfolio and claims operating metrics."""
    now = datetime.now()
    day_start, day_end = _day_bounds(now)

    active_policies = int(
        await db.scalar(
            select(func.count(Policy.id)).where(Policy.status == PolicyStatus.active)
        )
        or 0
    )
    total_workers = int(
        await db.scalar(
            select(func.count(Worker.id)).where(Worker.status == WorkerStatus.active)
        )
        or 0
    )
    claims_today = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.created_at >= day_start, Claim.created_at < day_end
            )
        )
        or 0
    )
    claims_approved = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.created_at >= day_start,
                Claim.created_at < day_end,
                Claim.decision == "approved",
            )
        )
        or 0
    )
    claims_held = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.created_at >= day_start,
                Claim.created_at < day_end,
                Claim.decision == "held",
            )
        )
        or 0
    )
    claims_rejected = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.created_at >= day_start,
                Claim.created_at < day_end,
                Claim.decision == "rejected",
            )
        )
        or 0
    )

    fraud_flags = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.fraud_tier.in_([FraudTier.amber, FraudTier.red]),
                Claim.status.notin_([ClaimStatus.paid, ClaimStatus.rejected]),
            )
        )
        or 0
    )

    total_premiums_collected = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Premium.final_premium), Decimal("0"))).where(
                Premium.payment_status == PremiumPaymentStatus.paid
            )
        )
        or 0
    )
    total_payouts = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Payout.amount), Decimal("0"))).where(
                Payout.status == PayoutStatus.completed
            )
        )
        or 0
    )

    loss_ratio = (
        Decimal("0")
        if total_premiums_collected <= 0
        else (total_payouts / total_premiums_collected)
    )
    reserve_pool = max(Decimal("0"), total_premiums_collected - total_payouts)

    return {
        "active_policies": active_policies,
        "total_workers": total_workers,
        "loss_ratio": float(round(loss_ratio, 4)),
        "claims_today": claims_today,
        "claims_approved": claims_approved,
        "claims_held": claims_held,
        "claims_rejected": claims_rejected,
        "fraud_flags": fraud_flags,
        "total_premiums_collected": float(total_premiums_collected),
        "total_payouts": float(total_payouts),
        "reserve_pool": float(reserve_pool),
    }


@router.get("/risk-map")
async def risk_map(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Return zone-level risk, active events, and in-progress claim indicators for map rendering."""
    now = datetime.now()
    day_start, day_end = _day_bounds(now)
    redis_client = getattr(request.app.state, "redis", None)

    active_events = list(
        (
            await db.execute(
                select(Event)
                .where(Event.lifecycle_phase.in_(["onset", "active", "peak"]))
                .order_by(Event.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    zones_output = []
    for h3_cell, meta in PremiumService.ZONES_META.items():
        lat, lng = ZONE_COORDS.get(h3_cell, (12.96, 77.60))

        risk_score = Decimal(meta["base_risk"])
        if redis_client is not None:
            cached = await redis_client.get(f"zone:risk:{h3_cell}")
            if cached is not None:
                risk_score = Decimal(str(cached))

        zone_active_event = None
        zone_event_severity = None
        for event in active_events:
            if h3_cell in (event.affected_zones or []):
                zone_active_event = event.event_type
                zone_event_severity = event.severity
                break

        active_workers = int(
            await db.scalar(
                select(func.count(Worker.id)).where(
                    Worker.primary_zones.op("?")(h3_cell),
                    Worker.status == WorkerStatus.active,
                )
            )
            or 0
        )

        claims_in_progress = int(
            await db.scalar(
                select(func.count(Claim.id))
                .select_from(Claim)
                .join(Event, Claim.event_id == Event.id)
                .where(
                    Claim.created_at >= day_start,
                    Claim.created_at < day_end,
                    Claim.status.in_([ClaimStatus.pending, ClaimStatus.approved]),
                    Event.affected_zones.op("?")(h3_cell),
                )
            )
            or 0
        )

        zones_output.append(
            {
                "h3_cell": h3_cell,
                "name": str(meta["name"]),
                "lat": lat,
                "lng": lng,
                "risk_score": float(risk_score),
                "base_risk": float(Decimal(meta["base_risk"])),
                "active_event": zone_active_event,
                "event_severity": zone_event_severity,
                "active_workers": active_workers,
                "claims_in_progress": claims_in_progress,
            }
        )

    active_events_response = [
        {
            "event_id": str(event.id),
            "compound_event_id": event.compound_event_id,
            "event_type": event.event_type,
            "severity": event.severity,
            "affected_zones": event.affected_zones or [],
            "zones_count": len(event.affected_zones or []),
            "onset_time": event.onset_time,
            "lifecycle_phase": event.lifecycle_phase,
            "claims_triggered": event.claims_triggered,
            "total_payout": float(event.total_payout or 0),
        }
        for event in active_events
    ]

    return {"zones": zones_output, "active_events": active_events_response}


@router.get("/claims-summary")
async def claims_summary(db: AsyncSession = Depends(get_db)) -> dict:
    """Return recent claims list, status/event aggregations, and payout summary for operations monitoring."""
    now = datetime.now()
    day_start, day_end = _day_bounds(now)

    recent_claim_rows = await db.execute(
        select(Claim, Worker.name, Event.event_type)
        .join(Worker, Claim.worker_id == Worker.id)
        .join(Event, Claim.event_id == Event.id)
        .order_by(Claim.created_at.desc())
        .limit(50)
    )

    recent_claims = []
    by_status: dict[str, int] = {"approved": 0, "held": 0, "rejected": 0, "pending": 0}
    by_event_type: dict[str, int] = {}

    for claim, worker_name, event_type in recent_claim_rows.all():
        decision_key = claim.decision.value if claim.decision else "pending"
        by_status[decision_key] = by_status.get(decision_key, 0) + 1
        by_event_type[event_type] = by_event_type.get(event_type, 0) + 1
        recent_claims.append(
            {
                "claim_id": str(claim.id),
                "worker_name": worker_name,
                "event_type": event_type,
                "expected_income": float(claim.expected_income or 0),
                "actual_income": float(claim.actual_income or 0),
                "causal_gap": float(claim.causal_gap or 0),
                "final_payout": float(claim.final_payout or 0),
                "fraud_score": float(claim.fraud_score or 0),
                "fraud_tier": claim.fraud_tier.value if claim.fraud_tier else None,
                "decision": claim.decision.value if claim.decision else None,
                "decision_reasoning": claim.decision_reasoning,
                "status": claim.status.value if claim.status else None,
                "created_at": claim.created_at,
            }
        )

    total_payout_today = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Payout.amount), Decimal("0"))).where(
                Payout.status == PayoutStatus.completed,
                Payout.completed_at >= day_start,
                Payout.completed_at < day_end,
            )
        )
        or 0
    )
    avg_payout = Decimal(
        await db.scalar(
            select(func.coalesce(func.avg(Claim.final_payout), Decimal("0"))).where(
                Claim.decision == "approved",
                Claim.created_at >= day_start,
                Claim.created_at < day_end,
            )
        )
        or 0
    )

    return {
        "recent_claims": recent_claims,
        "by_status": by_status,
        "by_event_type": by_event_type,
        "total_payout_today": float(total_payout_today),
        "avg_payout": float(avg_payout),
    }


@router.get("/premium-analytics")
async def premium_analytics(db: AsyncSession = Depends(get_db)) -> dict:
    """Return premium distribution, plan mix, and worker-level premium records."""
    avg_premium = Decimal(
        await db.scalar(
            select(func.coalesce(func.avg(Policy.weekly_premium), Decimal("0"))).where(
                Policy.status == PolicyStatus.active
            )
        )
        or 0
    )
    total_collected = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Premium.final_premium), Decimal("0"))).where(
                Premium.payment_status == PremiumPaymentStatus.paid
            )
        )
        or 0
    )

    premiums = list((await db.execute(select(Policy.weekly_premium))).scalars().all())
    buckets = {
        "0-100": 0,
        "100-150": 0,
        "150-200": 0,
        "200-300": 0,
        "300+": 0,
    }
    for premium in premiums:
        value = float(premium or 0)
        if value < 100:
            buckets["0-100"] += 1
        elif value < 150:
            buckets["100-150"] += 1
        elif value < 200:
            buckets["150-200"] += 1
        elif value < 300:
            buckets["200-300"] += 1
        else:
            buckets["300+"] += 1

    by_plan_rows = (
        await db.execute(
            select(Policy.coverage_plan, func.count(Policy.id)).group_by(
                Policy.coverage_plan
            )
        )
    ).all()
    by_plan = {plan.value: count for plan, count in by_plan_rows}

    worker_rows = (
        await db.execute(
            select(
                Worker.id,
                Worker.name,
                Policy.coverage_plan,
                Policy.weekly_premium,
                Premium.zone_risk,
                Worker.primary_zones,
            )
            .join(Policy, Policy.worker_id == Worker.id)
            .outerjoin(Premium, Premium.policy_id == Policy.id)
            .order_by(Policy.created_at.desc())
            .limit(100)
        )
    ).all()
    workers_with_premiums = [
        {
            "worker_id": str(worker_id),
            "worker_name": worker_name,
            "plan": plan.value,
            "premium": float(premium or 0),
            "zone_risk": float(zone_risk or 0),
            "zones": zones or [],
        }
        for worker_id, worker_name, plan, premium, zone_risk, zones in worker_rows
    ]

    distribution = [{"range": key, "count": value} for key, value in buckets.items()]

    return {
        "avg_premium": float(avg_premium),
        "total_collected": float(total_collected),
        "premium_distribution": distribution,
        "by_plan": by_plan,
        "workers_with_premiums": workers_with_premiums,
    }


@router.get("/loss-ratio")
async def loss_ratio(db: AsyncSession = Depends(get_db)) -> dict:
    """Return 12-week loss-ratio history with simulated prior weeks and current actual week."""
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    current_premiums = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Premium.final_premium), Decimal("0"))).where(
                Premium.payment_status == PremiumPaymentStatus.paid,
                Premium.created_at >= week_start,
                Premium.created_at < week_end,
            )
        )
        or 0
    )
    current_payouts = Decimal(
        await db.scalar(
            select(func.coalesce(func.sum(Payout.amount), Decimal("0"))).where(
                Payout.status == PayoutStatus.completed,
                Payout.created_at >= week_start,
                Payout.created_at < week_end,
            )
        )
        or 0
    )
    current_claims = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.created_at >= week_start, Claim.created_at < week_end
            )
        )
        or 0
    )
    current_ratio = float(
        (current_payouts / current_premiums) if current_premiums > 0 else Decimal("0")
    )

    weekly_history = []
    ratios = []
    for i in range(11, 0, -1):
        wk_start = week_start - timedelta(weeks=i)
        wk_end = wk_start + timedelta(days=6)
        base_p = Decimal("7050") + Decimal(random.randint(-500, 500))
        base_pay = Decimal("4200") + Decimal(random.randint(-1000, 1000))
        lr = float(base_pay / base_p) if base_p > 0 else 0.0
        ratios.append(lr)
        weekly_history.append(
            {
                "week": f"W{wk_start.isocalendar().week}",
                "week_label": f"{wk_start.strftime('%b %d')}-{wk_end.strftime('%d')}",
                "premiums_collected": float(base_p),
                "payouts": float(base_pay),
                "loss_ratio": lr,
                "claims_count": random.randint(8, 25),
            }
        )

    weekly_history.append(
        {
            "week": f"W{week_start.isocalendar().week}",
            "week_label": f"{week_start.strftime('%b %d')}-{(week_start + timedelta(days=6)).strftime('%d')}",
            "premiums_collected": float(current_premiums),
            "payouts": float(current_payouts),
            "loss_ratio": current_ratio,
            "claims_count": current_claims,
        }
    )
    ratios.append(current_ratio)

    recent = ratios[-4:] if len(ratios) >= 4 else ratios
    trend = "stable"
    if len(recent) >= 2:
        if recent[-1] > recent[0] + 0.05:
            trend = "rising"
        elif recent[-1] < recent[0] - 0.05:
            trend = "falling"

    return {
        "weekly_history": weekly_history,
        "current_week": weekly_history[-1],
        "target_range": [0.65, 0.75],
        "trend": trend,
    }


@router.get("/fraud-queue")
async def fraud_queue(db: AsyncSession = Depends(get_db)) -> dict:
    """Return pending fraud review queue and today's resolved-review count."""
    now = datetime.now()
    day_start, day_end = _day_bounds(now)

    pending_rows = (
        await db.execute(
            select(Claim, Worker.name, Event.event_type)
            .join(Worker, Claim.worker_id == Worker.id)
            .join(Event, Claim.event_id == Event.id)
            .where(
                Claim.fraud_tier.in_([FraudTier.amber, FraudTier.red]),
                Claim.status.notin_([ClaimStatus.paid, ClaimStatus.rejected]),
            )
            .order_by(Claim.created_at.desc())
        )
    ).all()

    pending_reviews = [
        {
            "claim_id": str(claim.id),
            "worker_name": worker_name,
            "worker_id": str(claim.worker_id),
            "fraud_score": float(claim.fraud_score or 0),
            "fraud_flags": claim.fraud_flags or [],
            "fraud_tier": claim.fraud_tier.value if claim.fraud_tier else None,
            "event_type": event_type,
            "expected_income": float(claim.expected_income or 0),
            "actual_income": float(claim.actual_income or 0),
            "final_payout": float(claim.final_payout or 0),
            "provisional_amount": float(claim.provisional_amount or 0),
            "created_at": claim.created_at,
        }
        for claim, worker_name, event_type in pending_rows
    ]

    resolved_today = int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.decided_at >= day_start,
                Claim.decided_at < day_end,
                Claim.status.in_([ClaimStatus.paid, ClaimStatus.rejected]),
            )
        )
        or 0
    )

    return {
        "pending_reviews": pending_reviews,
        "total_pending": len(pending_reviews),
        "resolved_today": resolved_today,
    }
