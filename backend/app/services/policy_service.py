from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Policy, PolicyStatus
from app.models.premium import Premium, PremiumPaymentStatus
from app.models.worker import Worker, WorkerStatus
from app.schemas.policy import PolicyCreate, PolicyUpdate
from app.services.premium_service import PremiumService


class PolicyServiceError(Exception):
    pass


PLAN_DISRUPTIONS = {
    "basic": ["HEAVY_RAINFALL", "FLOODING"],
    "standard": [
        "HEAVY_RAINFALL",
        "FLOODING",
        "EXTREME_HEAT",
        "SEVERE_AQI",
        "TRANSPORT_STRIKE",
        "CURFEW",
    ],
    "complete": [
        "HEAVY_RAINFALL",
        "FLOODING",
        "EXTREME_HEAT",
        "SEVERE_AQI",
        "TRANSPORT_STRIKE",
        "CURFEW",
        "PLATFORM_OUTAGE",
    ],
}

PLAN_MAX_PER_EVENT = {
    "basic": Decimal("500"),
    "standard": Decimal("800"),
    "complete": Decimal("1200"),
}

PLAN_COPAY = {
    "basic": Decimal("0.30"),
    "standard": Decimal("0.25"),
    "complete": Decimal("0.15"),
}


class PolicyService:
    @staticmethod
    async def _get_worker_or_raise(session: AsyncSession, worker_id) -> Worker:
        worker = await session.get(Worker, worker_id)
        if worker is None:
            raise PolicyServiceError("worker not found")
        if worker.status != WorkerStatus.active:
            raise PolicyServiceError("worker is not active")
        return worker

    @staticmethod
    async def _ensure_no_active_policy(session: AsyncSession, worker_id) -> None:
        active_policy = await session.scalar(
            select(Policy).where(
                Policy.worker_id == worker_id,
                Policy.status == PolicyStatus.active,
            )
        )
        if active_policy is not None:
            raise PolicyServiceError("worker already has an active policy")

    @staticmethod
    async def create_policy(
        session: AsyncSession,
        payload: PolicyCreate,
        coverage_start: datetime | None = None,
        coverage_end: datetime | None = None,
        previous_policy_id=None,
        renewal_count: int = 0,
    ) -> tuple[Policy, Premium]:
        worker = await PolicyService._get_worker_or_raise(session, payload.worker_id)
        await PolicyService._ensure_no_active_policy(session, payload.worker_id)

        breakdown = PremiumService.calculate_premium(worker, payload.coverage_plan)
        start = coverage_start or datetime.now()
        end = coverage_end or (start + timedelta(days=7))

        plan_key = payload.coverage_plan.value
        policy = Policy(
            worker_id=payload.worker_id,
            coverage_plan=payload.coverage_plan,
            coverage_start=start,
            coverage_end=end,
            weekly_premium=breakdown["final_premium"],
            premium_paid=False,
            covered_disruptions=PLAN_DISRUPTIONS[plan_key],
            max_per_event=PLAN_MAX_PER_EVENT[plan_key],
            copay_rate=PLAN_COPAY[plan_key],
            status=PolicyStatus.created,
            previous_policy_id=previous_policy_id,
            renewal_count=renewal_count,
        )
        session.add(policy)
        try:
            await session.flush()
            premium = await PremiumService.create_premium_record(
                session=session,
                worker=worker,
                policy_id=policy.id,
                coverage_plan=payload.coverage_plan,
            )
            await session.commit()
        except (IntegrityError, PolicyServiceError) as exc:
            await session.rollback()
            if isinstance(exc, PolicyServiceError):
                raise
            raise PolicyServiceError("failed to create policy") from exc

        await session.refresh(policy)
        await session.refresh(premium)
        return policy, premium

    @staticmethod
    async def list_policies(session: AsyncSession) -> list[Policy]:
        result = await session.execute(
            select(Policy).order_by(Policy.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_policy(session: AsyncSession, policy_id: str) -> Policy | None:
        return await session.get(Policy, policy_id)

    @staticmethod
    async def update_policy(
        session: AsyncSession, policy: Policy, payload: PolicyUpdate
    ) -> Policy:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(policy, key, value)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise PolicyServiceError("policy update failed") from exc
        await session.refresh(policy)
        return policy

    @staticmethod
    async def activate_policy(session: AsyncSession, policy: Policy) -> Policy:
        policy.status = PolicyStatus.active
        policy.premium_paid = True
        premium = await session.scalar(
            select(Premium)
            .where(Premium.policy_id == policy.id)
            .order_by(Premium.created_at.desc())
        )
        if premium:
            premium.payment_status = PremiumPaymentStatus.paid
            premium.paid_at = datetime.now()
        await session.commit()
        await session.refresh(policy)
        return policy

    @staticmethod
    async def cancel_policy(session: AsyncSession, policy: Policy) -> Policy:
        if policy.status == PolicyStatus.cancelled:
            raise PolicyServiceError("policy already cancelled")
        policy.status = PolicyStatus.cancelled
        await session.commit()
        await session.refresh(policy)
        return policy

    @staticmethod
    async def renew_policy(
        session: AsyncSession, policy: Policy
    ) -> tuple[Policy, Premium]:
        worker = await PolicyService._get_worker_or_raise(session, policy.worker_id)

        if policy.status in {PolicyStatus.cancelled, PolicyStatus.lapsed}:
            raise PolicyServiceError("cannot renew a cancelled or lapsed policy")

        new_start = policy.coverage_end
        new_end = new_start + timedelta(days=7)
        create_payload = PolicyCreate(
            worker_id=policy.worker_id, coverage_plan=policy.coverage_plan
        )

        policy.status = PolicyStatus.renewed

        breakdown = PremiumService.calculate_premium(worker, policy.coverage_plan)
        new_policy = Policy(
            worker_id=policy.worker_id,
            coverage_plan=policy.coverage_plan,
            coverage_start=new_start,
            coverage_end=new_end,
            weekly_premium=breakdown["final_premium"],
            premium_paid=False,
            covered_disruptions=policy.covered_disruptions,
            max_per_event=policy.max_per_event,
            copay_rate=policy.copay_rate,
            status=PolicyStatus.created,
            previous_policy_id=policy.id,
            renewal_count=policy.renewal_count + 1,
        )
        session.add(new_policy)
        await session.flush()
        premium = await PremiumService.create_premium_record(
            session=session,
            worker=worker,
            policy_id=new_policy.id,
            coverage_plan=create_payload.coverage_plan,
        )
        await session.commit()
        await session.refresh(new_policy)
        await session.refresh(premium)
        return new_policy, premium

    @staticmethod
    async def get_worker_policies(session: AsyncSession, worker_id) -> list[Policy]:
        result = await session.execute(
            select(Policy)
            .where(Policy.worker_id == worker_id)
            .order_by(Policy.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_latest_premium_for_policy(
        session: AsyncSession, policy_id
    ) -> Premium | None:
        return await session.scalar(
            select(Premium)
            .where(Premium.policy_id == policy_id)
            .order_by(Premium.created_at.desc())
        )
