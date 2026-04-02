import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.claim import Claim, ClaimDecision, ClaimStatus, FraudTier
from app.models.event import Event
from app.models.payout import Payout, PayoutStatus, PayoutType
from app.models.policy import Policy, PolicyStatus
from app.models.worker import WorkPatternType, Worker, WorkerStatus
from app.services.premium_service import PremiumService

logger = logging.getLogger(__name__)


class ClaimsPipelineError(Exception):
    pass


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def estimate_expected_income(worker: Worker, hours_in_period: Decimal) -> Decimal:
    weekly_hours_map = {
        WorkPatternType.full_time: Decimal("50"),
        WorkPatternType.part_time: Decimal("28"),
        WorkPatternType.weekends: Decimal("16"),
    }
    base_hours = weekly_hours_map[worker.work_pattern]
    hourly_rate = Decimal(worker.weekly_avg_income) / base_hours

    current_hour = datetime.now().hour
    if 12 <= current_hour <= 14 or 19 <= current_hour <= 22:
        hourly_rate *= Decimal("1.3")
    elif 14 < current_hour < 19:
        hourly_rate *= Decimal("0.7")

    return _round_money(hourly_rate * hours_in_period)


async def count_claims_last_7_days(db: AsyncSession, worker_id: UUID) -> int:
    since = datetime.now() - timedelta(days=7)
    return int(
        await db.scalar(
            select(func.count(Claim.id)).where(
                Claim.worker_id == worker_id,
                Claim.created_at >= since,
            )
        )
        or 0
    )


async def _get_actual_income(
    worker_id: UUID, start: datetime, end: datetime
) -> Decimal:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.sim_platform_url}/sim/platform/worker-earnings",
                params={
                    "worker_id": str(worker_id),
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
            )
            response.raise_for_status()
            payload = response.json()
            return Decimal(str(payload.get("total_earnings", 0) or 0))
        except Exception as exc:
            logger.warning(
                "Failed worker earnings fetch worker_id=%s err=%s", worker_id, exc
            )
            return Decimal("0")


async def _get_control_data(
    event_id: UUID,
    start: datetime,
    end: datetime,
    affected_zones: list[str],
) -> tuple[Decimal, Decimal]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.sim_platform_url}/sim/platform/control-zone-earnings",
                params={
                    "event_id": str(event_id),
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
            )
            response.raise_for_status()
            payload = response.json()
            return (
                Decimal(str(payload.get("avg_expected", 0) or 0)),
                Decimal(str(payload.get("avg_actual", 0) or 0)),
            )
        except Exception:
            zone_keys = list(PremiumService.ZONES_META.keys())
            control_candidates = [
                zone for zone in zone_keys if zone not in affected_zones
            ][:5]
            if not control_candidates:
                return Decimal("100"), Decimal("90")
            synthetic_expected = Decimal("100")
            synthetic_actual = Decimal("90")
            return synthetic_expected, synthetic_actual


def _determine_fraud(
    worker: Worker, event: Event, recent_claim_count: int
) -> tuple[Decimal, list[str], FraudTier]:
    fraud_score = Decimal("0")
    fraud_flags: list[str] = []

    worker_zones = set(worker.primary_zones or [])
    affected = set(event.affected_zones or [])
    if not worker_zones.intersection(affected):
        fraud_score += Decimal("0.25")
        fraud_flags.append("UNFAMILIAR_ZONE")

    current_hour = datetime.now().hour
    typical = worker.typical_hours or []
    hour_map = {"morning": (6, 12), "afternoon": (12, 17), "evening": (17, 23)}
    in_typical = any(
        hour_map.get(slot, (0, 0))[0] <= current_hour < hour_map.get(slot, (0, 0))[1]
        for slot in typical
    )
    if typical and not in_typical:
        fraud_score += Decimal("0.20")
        fraud_flags.append("UNUSUAL_HOURS")

    if recent_claim_count >= 3:
        fraud_score += Decimal("0.15")
        fraud_flags.append("HIGH_CLAIM_FREQUENCY")

    fraud_score = min(Decimal("1"), fraud_score)
    if fraud_score < Decimal("0.4"):
        tier = FraudTier.green
    elif fraud_score < Decimal("0.7"):
        tier = FraudTier.amber
    else:
        tier = FraudTier.red
    return fraud_score, fraud_flags, tier


async def evaluate_event(event_id: UUID, db: AsyncSession) -> dict[str, Any]:
    logger.info("Starting evaluate_event event_id=%s", event_id)
    event = await db.get(Event, event_id)
    if event is None:
        raise ClaimsPipelineError("event not found")

    now = datetime.now()
    onset = event.onset_time or now
    hours_in_period = Decimal(str(max((now - onset).total_seconds() / 3600, 1)))
    affected_zones = event.affected_zones or []

    workers_query = select(Worker).where(
        Worker.status == WorkerStatus.active,
        Worker.primary_zones.op("?|")(affected_zones),
    )
    workers_result = await db.execute(workers_query)
    workers = list(workers_result.scalars().all())

    control_expected, control_actual = await _get_control_data(
        event.id, onset, now, affected_zones
    )
    control_drop = max(Decimal("0"), control_expected - control_actual)

    workers_evaluated = 0
    claims_created = 0
    claims_approved = 0
    claims_held = 0
    claims_rejected = 0
    skipped_no_policy = 0
    total_payout = Decimal("0")

    for worker in workers:
        workers_evaluated += 1
        try:
            policy = await db.scalar(
                select(Policy)
                .where(
                    Policy.worker_id == worker.id,
                    Policy.status == PolicyStatus.active,
                    Policy.coverage_end > now,
                    Policy.covered_disruptions.op("?")(event.event_type),
                )
                .order_by(Policy.created_at.desc())
            )
            if policy is None:
                skipped_no_policy += 1
                continue

            existing = await db.scalar(
                select(Claim).where(
                    Claim.worker_id == worker.id,
                    Claim.compound_event_id == event.compound_event_id,
                )
            )
            if existing is not None:
                logger.info(
                    "Skipping duplicate claim worker_id=%s event=%s",
                    worker.id,
                    event.compound_event_id,
                )
                continue

            expected_income = estimate_expected_income(worker, hours_in_period)
            actual_income = _round_money(
                await _get_actual_income(worker.id, onset, now)
            )
            raw_gap = _round_money(expected_income - actual_income)
            if raw_gap <= 0:
                logger.info(
                    "No gap for worker worker_id=%s raw_gap=%s", worker.id, raw_gap
                )
                continue

            affected_drop = raw_gap
            disruption_caused_gap = max(Decimal("0"), affected_drop - control_drop)
            causal_fraction = (
                min(
                    Decimal("1"),
                    max(Decimal("0"), disruption_caused_gap / affected_drop),
                )
                if affected_drop > 0
                else Decimal("0")
            )
            causal_gap = _round_money(raw_gap * causal_fraction)

            drop_ratio = (
                causal_gap / expected_income if expected_income > 0 else Decimal("0")
            )
            if drop_ratio < Decimal("0.10"):
                claim = Claim(
                    policy_id=policy.id,
                    worker_id=worker.id,
                    event_id=event.id,
                    compound_event_id=event.compound_event_id,
                    expected_income=expected_income,
                    actual_income=actual_income,
                    raw_gap=raw_gap,
                    causal_fraction=causal_fraction,
                    causal_gap=causal_gap,
                    drop_ratio=drop_ratio,
                    payout_fraction=Decimal("0"),
                    coverage_rate=Decimal("0"),
                    calculated_payout=Decimal("0"),
                    final_payout=Decimal("0"),
                    fraud_score=Decimal("0"),
                    fraud_flags=[],
                    fraud_tier=FraudTier.green,
                    decision=ClaimDecision.rejected,
                    decision_reasoning=f"Income drop of {float(drop_ratio) * 100:.1f}% is below the 10% threshold",
                    decision_confidence=Decimal("0.95"),
                    status=ClaimStatus.rejected,
                    provisional_amount=Decimal("0"),
                    decided_at=now,
                )
                db.add(claim)
                await db.commit()
                claims_created += 1
                claims_rejected += 1
                continue

            if drop_ratio < Decimal("0.30"):
                payout_fraction = (drop_ratio - Decimal("0.10")) / Decimal("0.20")
            else:
                payout_fraction = Decimal("1.0")

            recent = await count_claims_last_7_days(db, worker.id)
            fraud_score, fraud_flags, fraud_tier = _determine_fraud(
                worker, event, recent
            )

            coverage_rate = Decimal("1") - Decimal(policy.copay_rate)
            calculated_payout = causal_gap * payout_fraction * coverage_rate
            max_daily = Decimal(worker.weekly_avg_income) * Decimal("0.25")
            final_payout = min(
                calculated_payout, Decimal(policy.max_per_event), max_daily
            )
            final_payout = Decimal(round(max(0, float(final_payout))))

            decision = ClaimDecision.approved
            claim_status = ClaimStatus.approved
            provisional_amount = Decimal("0")
            decision_confidence = Decimal("0.92")
            if fraud_tier == FraudTier.green:
                reasoning = (
                    f"{event.event_type} confirmed. Income drop {float(drop_ratio) * 100:.1f}%. "
                    f"Causal attribution: {float(causal_fraction) * 100:.0f}% disruption-caused. "
                    f"Fraud check: clear. Payout: Rs.{int(final_payout)}"
                )
            else:
                decision = ClaimDecision.held
                claim_status = ClaimStatus.under_review
                provisional_amount = Decimal(round(float(final_payout) * 0.5))
                decision_confidence = (
                    Decimal("0.75")
                    if fraud_tier == FraudTier.amber
                    else Decimal("0.65")
                )
                if fraud_tier == FraudTier.amber:
                    reasoning = f"Event confirmed but verification needed. Flags: {fraud_flags}. Provisional 50% payout."
                else:
                    reasoning = f"High fraud indicators: {fraud_flags}. Manual review required. Provisional 50% payout."

            claim = Claim(
                policy_id=policy.id,
                worker_id=worker.id,
                event_id=event.id,
                compound_event_id=event.compound_event_id,
                expected_income=expected_income,
                actual_income=actual_income,
                raw_gap=raw_gap,
                causal_fraction=causal_fraction,
                causal_gap=causal_gap,
                drop_ratio=drop_ratio,
                payout_fraction=payout_fraction,
                coverage_rate=coverage_rate,
                calculated_payout=calculated_payout,
                final_payout=final_payout,
                fraud_score=fraud_score,
                fraud_flags=fraud_flags,
                fraud_tier=fraud_tier,
                decision=decision,
                decision_reasoning=reasoning,
                decision_confidence=decision_confidence,
                status=claim_status,
                provisional_amount=provisional_amount,
                decided_at=now,
            )
            db.add(claim)
            await db.flush()

            payout_amount = Decimal("0")
            payout_type = None
            if decision == ClaimDecision.approved and final_payout > 0:
                payout_amount = final_payout
                payout_type = PayoutType.full
                claim.status = ClaimStatus.paid
                claim.paid_at = now
                claims_approved += 1
                worker.trust_score = min(
                    Decimal("1.00"), Decimal(worker.trust_score) + Decimal("0.01")
                )
            elif decision == ClaimDecision.held and provisional_amount > 0:
                payout_amount = provisional_amount
                payout_type = PayoutType.provisional
                claim.status = ClaimStatus.provisional_paid
                claims_held += 1
            else:
                claims_rejected += 1

            if payout_amount > 0 and payout_type:
                payout = Payout(
                    claim_id=claim.id,
                    worker_id=worker.id,
                    amount=_round_money(payout_amount),
                    payout_type=payout_type,
                    payment_method="upi",
                    upi_id=worker.upi_id,
                    status=PayoutStatus.completed,
                    completed_at=now,
                )
                db.add(payout)
                total_payout += payout.amount

            await db.commit()
            claims_created += 1
        except Exception as worker_exc:
            logger.exception(
                "Worker evaluation failed worker_id=%s event_id=%s err=%s",
                worker.id,
                event.id,
                worker_exc,
            )
            await db.rollback()
            continue

    event.claims_triggered = claims_created
    event.total_payout = _round_money(total_payout)
    event.lifecycle_phase = "active"
    await db.commit()

    summary = {
        "event_id": str(event.id),
        "compound_event_id": event.compound_event_id,
        "event_type": event.event_type,
        "workers_evaluated": workers_evaluated,
        "claims_created": claims_created,
        "claims_approved": claims_approved,
        "claims_held": claims_held,
        "claims_rejected": claims_rejected,
        "total_payout": _round_money(total_payout),
        "skipped_no_policy": skipped_no_policy,
    }
    logger.info("Completed evaluate_event summary=%s", summary)
    return summary


class ClaimsPipeline:
    @staticmethod
    async def list_claims(
        session: AsyncSession,
        status: ClaimStatus | None = None,
        worker_id: UUID | None = None,
        event_id: UUID | None = None,
        fraud_tier: FraudTier | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Claim], int]:
        query = select(Claim)
        count_query = select(func.count(Claim.id))

        if status:
            query = query.where(Claim.status == status)
            count_query = count_query.where(Claim.status == status)
        if worker_id:
            query = query.where(Claim.worker_id == worker_id)
            count_query = count_query.where(Claim.worker_id == worker_id)
        if event_id:
            query = query.where(Claim.event_id == event_id)
            count_query = count_query.where(Claim.event_id == event_id)
        if fraud_tier:
            query = query.where(Claim.fraud_tier == fraud_tier)
            count_query = count_query.where(Claim.fraud_tier == fraud_tier)

        offset = (page - 1) * limit
        result = await session.execute(
            query.order_by(Claim.created_at.desc()).offset(offset).limit(limit)
        )
        total = int(await session.scalar(count_query) or 0)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_claim(session: AsyncSession, claim_id: UUID) -> Claim | None:
        return await session.get(Claim, claim_id)

    @staticmethod
    async def review_claim(
        session: AsyncSession,
        claim: Claim,
        decision: str,
        reviewer_notes: str | None,
    ) -> Claim:
        if claim.status not in {ClaimStatus.under_review, ClaimStatus.provisional_paid}:
            raise ClaimsPipelineError("claim is not eligible for manual review")

        worker = await session.get(Worker, claim.worker_id)
        if worker is None:
            raise ClaimsPipelineError("claim worker not found")

        now = datetime.now()
        if decision == "approve":
            remaining = Decimal(claim.final_payout or 0) - Decimal(
                claim.provisional_amount or 0
            )
            if remaining > 0:
                payout = Payout(
                    claim_id=claim.id,
                    worker_id=claim.worker_id,
                    amount=_round_money(remaining),
                    payout_type=PayoutType.full,
                    payment_method="upi",
                    upi_id=worker.upi_id,
                    status=PayoutStatus.completed,
                    completed_at=now,
                )
                session.add(payout)
            claim.decision = ClaimDecision.approved
            claim.status = ClaimStatus.paid
            claim.paid_at = now
            worker.trust_score = min(
                Decimal("1.00"), Decimal(worker.trust_score) + Decimal("0.01")
            )
            claim.decision_reasoning = reviewer_notes or "Manual review approved"
        else:
            claim.decision = ClaimDecision.rejected
            claim.status = ClaimStatus.rejected
            worker.trust_score = max(
                Decimal("0.00"), Decimal(worker.trust_score) - Decimal("0.05")
            )
            claim.decision_reasoning = reviewer_notes or "Manual review rejected"

        claim.decided_at = now
        await session.commit()
        await session.refresh(claim)
        return claim


async def trigger_scenario_and_evaluate(
    db: AsyncSession, scenario: str
) -> dict[str, Any]:
    from app.services.event_detection import scan_for_events

    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.post(
            f"{settings.sim_weather_url}/sim/orchestrator/trigger-scenario",
            json={"scenario": scenario, "time_compression": 10},
        )
    await asyncio.sleep(5)

    events = await scan_for_events(db, run_evaluation=False)
    if not events:
        return {
            "event_id": "",
            "compound_event_id": "",
            "event_type": "NONE",
            "workers_evaluated": 0,
            "claims_created": 0,
            "claims_approved": 0,
            "claims_held": 0,
            "claims_rejected": 0,
            "total_payout": Decimal("0"),
            "skipped_no_policy": 0,
        }
    return await evaluate_event(events[0].id, db)
