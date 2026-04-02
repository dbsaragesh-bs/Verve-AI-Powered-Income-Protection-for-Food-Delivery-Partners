from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import CoveragePlanType
from app.models.premium import Premium
from app.models.worker import WorkPatternType, Worker
from app.schemas.premium import PremiumCreate, PremiumUpdate


class PremiumServiceError(Exception):
    pass


class PremiumService:
    ZONES_META: dict[str, dict[str, Decimal | str]] = {
        "8928308280fffff": {
            "name": "Koramangala Block 5",
            "base_risk": Decimal("0.45"),
        },
        "8928308281fffff": {"name": "Indiranagar", "base_risk": Decimal("0.20")},
        "8928308282fffff": {"name": "HSR Layout", "base_risk": Decimal("0.40")},
        "8928308283fffff": {"name": "Whitefield", "base_risk": Decimal("0.15")},
        "8928308284fffff": {"name": "Majestic", "base_risk": Decimal("0.65")},
        "8928308285fffff": {"name": "Electronic City", "base_risk": Decimal("0.12")},
        "8928308286fffff": {"name": "Marathahalli", "base_risk": Decimal("0.25")},
        "8928308287fffff": {"name": "Jayanagar", "base_risk": Decimal("0.20")},
        "8928308288fffff": {"name": "MG Road", "base_risk": Decimal("0.15")},
        "8928308289fffff": {"name": "KR Market", "base_risk": Decimal("0.70")},
    }

    EXPOSURE_BY_WORK_PATTERN: dict[WorkPatternType, Decimal] = {
        WorkPatternType.full_time: Decimal("0.85"),
        WorkPatternType.part_time: Decimal("0.55"),
        WorkPatternType.weekends: Decimal("0.35"),
    }

    PLAN_MULTIPLIER: dict[CoveragePlanType, Decimal] = {
        CoveragePlanType.basic: Decimal("0.55"),
        CoveragePlanType.standard: Decimal("1.00"),
        CoveragePlanType.complete: Decimal("1.45"),
    }

    INCOME_LOSS_RATE = Decimal("0.18")
    OPERATING_MARGIN = Decimal("15.0")
    CATASTROPHE_LOADING = Decimal("8.0")
    MINIMUM_PREMIUM = Decimal("39")

    @staticmethod
    def _round_money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _zone_risk(cls, zones: list[str]) -> Decimal:
        if not zones:
            raise PremiumServiceError("worker has no primary zones configured")
        known_risks: list[Decimal] = []
        for zone in zones:
            meta = cls.ZONES_META.get(zone)
            if meta:
                known_risks.append(meta["base_risk"])
        if not known_risks:
            return Decimal("0.25")
        return (sum(known_risks) / Decimal(len(known_risks))).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _uncertainty_buffer(data_weeks: int) -> Decimal:
        if data_weeks >= 8:
            return Decimal("1.10")
        if data_weeks >= 4:
            return Decimal("1.20")
        return Decimal("1.35")

    @classmethod
    def calculate_premium(
        cls,
        worker: Worker,
        coverage_plan: CoveragePlanType,
    ) -> dict[str, Decimal]:
        if worker.weekly_avg_income is None or worker.weekly_avg_income <= 0:
            raise PremiumServiceError(
                "worker weekly_avg_income must be greater than zero"
            )

        zone_risk = cls._zone_risk(worker.primary_zones)
        exposure_score = cls.EXPOSURE_BY_WORK_PATTERN[worker.work_pattern]
        income_loss_rate = cls.INCOME_LOSS_RATE
        weekly_income = Decimal(worker.weekly_avg_income)
        uncertainty_buffer = cls._uncertainty_buffer(worker.data_weeks)
        plan_multiplier = cls.PLAN_MULTIPLIER[coverage_plan]

        expected_loss = zone_risk * exposure_score * income_loss_rate * weekly_income
        premium_base = (
            expected_loss * uncertainty_buffer
            + cls.OPERATING_MARGIN
            + cls.CATASTROPHE_LOADING
        )
        final_premium = premium_base * plan_multiplier
        final_premium = max(cls._round_money(final_premium), cls.MINIMUM_PREMIUM)

        return {
            "zone_risk": zone_risk,
            "exposure_score": exposure_score,
            "income_loss_rate": income_loss_rate,
            "weekly_income": cls._round_money(weekly_income),
            "expected_loss": cls._round_money(expected_loss),
            "uncertainty_buffer": uncertainty_buffer,
            "operating_margin": cls.OPERATING_MARGIN,
            "catastrophe_loading": cls.CATASTROPHE_LOADING,
            "plan_multiplier": plan_multiplier,
            "final_premium": final_premium,
        }

    @classmethod
    def calculate_plan_comparison(
        cls, worker: Worker
    ) -> dict[CoveragePlanType, Decimal]:
        output: dict[CoveragePlanType, Decimal] = {}
        for plan in CoveragePlanType:
            breakdown = cls.calculate_premium(worker, plan)
            output[plan] = breakdown["final_premium"]
        return output

    @classmethod
    async def create_premium_record(
        cls,
        session: AsyncSession,
        worker: Worker,
        policy_id,
        coverage_plan: CoveragePlanType,
    ) -> Premium:
        breakdown = cls.calculate_premium(worker, coverage_plan)
        today = date.today()
        premium = Premium(
            policy_id=policy_id,
            worker_id=worker.id,
            week_start=today,
            week_end=today + timedelta(days=6),
            zone_risk=breakdown["zone_risk"],
            exposure_score=breakdown["exposure_score"],
            income_loss_rate=breakdown["income_loss_rate"],
            weekly_income=breakdown["weekly_income"],
            expected_loss=breakdown["expected_loss"],
            uncertainty_buffer=breakdown["uncertainty_buffer"],
            operating_margin=breakdown["operating_margin"],
            catastrophe_loading=breakdown["catastrophe_loading"],
            plan_multiplier=breakdown["plan_multiplier"],
            final_premium=breakdown["final_premium"],
        )
        session.add(premium)
        await session.flush()
        return premium

    @staticmethod
    async def list_worker_premium_history(
        session: AsyncSession, worker_id, weeks: int = 12
    ) -> list[Premium]:
        result = await session.execute(
            select(Premium)
            .where(Premium.worker_id == worker_id)
            .order_by(Premium.created_at.desc())
            .limit(weeks)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_premium(session: AsyncSession, payload: PremiumCreate) -> Premium:
        premium = Premium(**payload.model_dump())
        session.add(premium)
        await session.commit()
        await session.refresh(premium)
        return premium

    @staticmethod
    async def list_premiums(session: AsyncSession) -> list[Premium]:
        result = await session.execute(
            select(Premium).order_by(Premium.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_premium(session: AsyncSession, premium_id: str) -> Premium | None:
        return await session.get(Premium, premium_id)

    @staticmethod
    async def update_premium(
        session: AsyncSession, premium: Premium, payload: PremiumUpdate
    ) -> Premium:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(premium, key, value)
        await session.commit()
        await session.refresh(premium)
        return premium
