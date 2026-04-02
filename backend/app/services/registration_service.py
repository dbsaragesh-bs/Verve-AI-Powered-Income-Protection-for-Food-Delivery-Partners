from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import CoveragePlanType, Policy, PolicyStatus
from app.models.worker import Worker
from app.schemas.worker import WorkerCreate, WorkerUpdate
from app.services.premium_service import PremiumService


class RegistrationServiceError(Exception):
    pass


class RegistrationService:
    CLUSTER_BY_WORK_PATTERN = {
        "full_time": 1,
        "part_time": 2,
        "weekends": 3,
    }

    INCOME_BY_CLUSTER = {
        1: Decimal("5500"),
        2: Decimal("2800"),
        3: Decimal("2000"),
    }

    @staticmethod
    async def create_worker(session: AsyncSession, payload: WorkerCreate) -> Worker:
        existing = await session.scalar(
            select(Worker).where(Worker.phone == payload.phone)
        )
        if existing is not None:
            raise RegistrationServiceError("worker with this phone already exists")

        cluster_id = RegistrationService.CLUSTER_BY_WORK_PATTERN[
            payload.work_pattern.value
        ]
        weekly_income = RegistrationService.INCOME_BY_CLUSTER[cluster_id]

        worker = Worker(
            **payload.model_dump(),
            cluster_id=cluster_id,
            weekly_avg_income=weekly_income,
        )
        session.add(worker)
        try:
            await session.flush()
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise RegistrationServiceError(
                "worker with this phone already exists"
            ) from exc
        await session.refresh(worker)
        return worker

    @staticmethod
    def get_suggested_premiums(worker: Worker) -> dict[CoveragePlanType, Decimal]:
        return PremiumService.calculate_plan_comparison(worker)

    @staticmethod
    async def get_active_policy(session: AsyncSession, worker_id) -> Policy | None:
        return await session.scalar(
            select(Policy)
            .where(Policy.worker_id == worker_id, Policy.status == PolicyStatus.active)
            .order_by(Policy.created_at.desc())
        )

    @staticmethod
    async def list_workers(
        session: AsyncSession,
        city: str | None = None,
        platform=None,
        status=None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Worker], int]:
        query = select(Worker)
        count_query = select(func.count(Worker.id))

        if city:
            query = query.where(Worker.city == city)
            count_query = count_query.where(Worker.city == city)
        if platform:
            query = query.where(Worker.platform == platform)
            count_query = count_query.where(Worker.platform == platform)
        if status:
            query = query.where(Worker.status == status)
            count_query = count_query.where(Worker.status == status)

        offset = (page - 1) * limit
        result = await session.execute(
            query.order_by(Worker.created_at.desc()).offset(offset).limit(limit)
        )
        count_result = await session.scalar(count_query)
        workers = list(result.scalars().all())
        total = int(count_result or 0)
        return workers, total

    @staticmethod
    async def get_worker(session: AsyncSession, worker_id: str) -> Worker | None:
        return await session.get(Worker, worker_id)

    @staticmethod
    async def update_worker(
        session: AsyncSession, worker: Worker, payload: WorkerUpdate
    ) -> Worker:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(worker, key, value)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ValueError("update violates a unique constraint") from exc
        await session.refresh(worker)
        return worker
