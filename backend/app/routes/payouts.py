import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.payout import PayoutCreate, PayoutRead, PayoutUpdate
from app.services.payout_service import PayoutService

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.post("", response_model=PayoutRead, status_code=status.HTTP_201_CREATED)
async def create_payout(
    payload: PayoutCreate, db: AsyncSession = Depends(get_db)
) -> PayoutRead:
    try:
        payout = await PayoutService.create_payout(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return PayoutRead.model_validate(payout)


@router.get("", response_model=list[PayoutRead])
async def list_payouts(db: AsyncSession = Depends(get_db)) -> list[PayoutRead]:
    payouts = await PayoutService.list_payouts(db)
    return [PayoutRead.model_validate(payout) for payout in payouts]


@router.get("/{payout_id}", response_model=PayoutRead)
async def get_payout(
    payout_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> PayoutRead:
    payout = await PayoutService.get_payout(db, str(payout_id))
    if payout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="payout not found"
        )
    return PayoutRead.model_validate(payout)


@router.patch("/{payout_id}", response_model=PayoutRead)
async def update_payout(
    payout_id: uuid.UUID,
    payload: PayoutUpdate,
    db: AsyncSession = Depends(get_db),
) -> PayoutRead:
    payout = await PayoutService.get_payout(db, str(payout_id))
    if payout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="payout not found"
        )
    updated = await PayoutService.update_payout(db, payout, payload)
    return PayoutRead.model_validate(updated)
