import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.worker import Worker
from app.schemas.premium import (
    PremiumBreakdownResponse,
    PremiumCalculationRequest,
    PremiumCalculationResponse,
    PremiumHistoryResponse,
    PremiumRead,
)
from app.services.premium_service import PremiumService, PremiumServiceError

router = APIRouter(prefix="/premiums", tags=["premiums"])


@router.post("/calculate", response_model=PremiumCalculationResponse)
async def calculate_premium(
    payload: PremiumCalculationRequest,
    db: AsyncSession = Depends(get_db),
) -> PremiumCalculationResponse:
    """Calculate premium breakdown for one plan and compare all plans for a worker."""
    worker = await db.get(Worker, payload.worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="worker not found"
        )

    try:
        breakdown = PremiumService.calculate_premium(worker, payload.coverage_plan)
        comparison = PremiumService.calculate_plan_comparison(worker)
    except PremiumServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return PremiumCalculationResponse(
        worker_id=worker.id,
        coverage_plan=payload.coverage_plan,
        breakdown=PremiumBreakdownResponse(**breakdown),
        plan_comparison=comparison,
    )


@router.get("/{worker_id}/history", response_model=PremiumHistoryResponse)
async def premium_history(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PremiumHistoryResponse:
    """Return the most recent 12 premium records for the worker."""
    worker = await db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="worker not found"
        )

    records = await PremiumService.list_worker_premium_history(db, worker_id, weeks=12)
    return PremiumHistoryResponse(
        worker_id=worker_id,
        records=[PremiumRead.model_validate(row) for row in records],
    )
