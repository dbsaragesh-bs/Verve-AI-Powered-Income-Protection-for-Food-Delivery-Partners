import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.policy import CoveragePlanType
from app.models.worker import PlatformType, WorkerStatus
from app.schemas.policy import PolicyRead
from app.schemas.worker import (
    ActivePolicySummary,
    SuggestedPremiums,
    WorkerCreate,
    WorkerListItem,
    WorkerListResponse,
    WorkerProfileResponse,
    WorkerRegistrationResponse,
)
from app.services.registration_service import (
    RegistrationService,
    RegistrationServiceError,
)
from app.services.policy_service import PolicyService

router = APIRouter(prefix="/workers", tags=["workers"])


@router.post(
    "/register",
    response_model=WorkerRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_worker(
    payload: WorkerCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkerRegistrationResponse:
    """Register a new delivery worker and return suggested premiums for all plans."""
    try:
        worker = await RegistrationService.create_worker(db, payload)
        suggested = RegistrationService.get_suggested_premiums(worker)
    except RegistrationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return WorkerRegistrationResponse(
        worker_id=worker.id,
        name=worker.name,
        platform=worker.platform,
        city=worker.city,
        primary_zones=worker.primary_zones,
        work_pattern=worker.work_pattern,
        cluster_id=worker.cluster_id or 0,
        weekly_avg_income=worker.weekly_avg_income,
        trust_score=worker.trust_score,
        status=worker.status,
        suggested_premiums=SuggestedPremiums(
            basic=suggested[CoveragePlanType.basic],
            standard=suggested[CoveragePlanType.standard],
            complete=suggested[CoveragePlanType.complete],
        ),
    )


@router.get("/{worker_id}", response_model=WorkerProfileResponse)
async def get_worker_profile(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkerProfileResponse:
    """Get the full worker profile including active policy summary if available."""
    worker = await RegistrationService.get_worker(db, str(worker_id))
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="worker not found"
        )

    active = await RegistrationService.get_active_policy(db, worker.id)
    active_policy = None
    if active is not None:
        active_policy = ActivePolicySummary(
            policy_id=active.id,
            coverage_plan=active.coverage_plan,
            weekly_premium=active.weekly_premium,
            coverage_start=active.coverage_start,
            coverage_end=active.coverage_end,
            status=active.status,
        )

    return WorkerProfileResponse(
        worker_id=worker.id,
        name=worker.name,
        phone=worker.phone,
        platform=worker.platform,
        partner_id=worker.partner_id,
        city=worker.city,
        primary_zones=worker.primary_zones,
        work_pattern=worker.work_pattern,
        typical_hours=worker.typical_hours,
        weekly_avg_income=worker.weekly_avg_income,
        trust_score=worker.trust_score,
        adaptation_score=worker.adaptation_score,
        upi_id=worker.upi_id,
        cluster_id=worker.cluster_id,
        data_weeks=worker.data_weeks,
        status=worker.status,
        created_at=worker.created_at,
        updated_at=worker.updated_at,
        active_policy=active_policy,
    )


@router.get("", response_model=WorkerListResponse)
async def list_workers(
    city: str | None = Query(default=None),
    platform: PlatformType | None = Query(default=None),
    status_filter: WorkerStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> WorkerListResponse:
    """List workers with optional filters and paginated results."""
    workers, total = await RegistrationService.list_workers(
        session=db,
        city=city,
        platform=platform,
        status=status_filter,
        page=page,
        limit=limit,
    )
    return WorkerListResponse(
        page=page,
        limit=limit,
        total=total,
        items=[
            WorkerListItem(
                worker_id=worker.id,
                name=worker.name,
                platform=worker.platform,
                city=worker.city,
                work_pattern=worker.work_pattern,
                cluster_id=worker.cluster_id,
                weekly_avg_income=worker.weekly_avg_income,
                status=worker.status,
            )
            for worker in workers
        ],
    )


@router.get("/{worker_id}/policies", response_model=list[PolicyRead])
async def get_worker_policy_history(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[PolicyRead]:
    """Return all policies for a worker sorted by most recent first."""
    worker = await RegistrationService.get_worker(db, str(worker_id))
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="worker not found"
        )
    policies = await PolicyService.get_worker_policies(db, worker_id)
    return [PolicyRead.model_validate(policy) for policy in policies]
