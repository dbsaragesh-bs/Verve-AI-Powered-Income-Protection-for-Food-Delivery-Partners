import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.policy import (
    PolicyCreate,
    PolicyRead,
    PolicyResponse,
    PremiumBreakdown,
)
from app.services.policy_service import PolicyService, PolicyServiceError

router = APIRouter(prefix="/policies", tags=["policies"])


def _to_policy_response(policy, premium) -> PolicyResponse:
    return PolicyResponse(
        policy_id=policy.id,
        worker_id=policy.worker_id,
        coverage_plan=policy.coverage_plan,
        weekly_premium=policy.weekly_premium,
        premium_breakdown=PremiumBreakdown(
            zone_risk=premium.zone_risk,
            exposure_score=premium.exposure_score,
            income_loss_rate=premium.income_loss_rate,
            weekly_income=premium.weekly_income,
            expected_loss=premium.expected_loss,
            uncertainty_buffer=premium.uncertainty_buffer,
            operating_margin=premium.operating_margin,
            catastrophe_loading=premium.catastrophe_loading,
            plan_multiplier=premium.plan_multiplier,
            final_premium=premium.final_premium,
        ),
        coverage_start=policy.coverage_start,
        coverage_end=policy.coverage_end,
        covered_disruptions=policy.covered_disruptions,
        max_per_event_payout=policy.max_per_event,
        copay_rate=policy.copay_rate,
        status=policy.status,
    )


@router.post(
    "/create", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED
)
async def create_policy(
    payload: PolicyCreate,
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Create a policy for an active worker and generate initial premium breakdown."""
    try:
        policy, premium = await PolicyService.create_policy(db, payload)
    except PolicyServiceError as exc:
        detail = str(exc)
        if detail == "worker not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=detail
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail
        ) from exc
    return _to_policy_response(policy, premium)


@router.post("/{policy_id}/activate", response_model=PolicyRead)
async def activate_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PolicyRead:
    """Activate policy and mark related premium as paid after payment confirmation."""
    policy = await PolicyService.get_policy(db, str(policy_id))
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="policy not found"
        )
    updated = await PolicyService.activate_policy(db, policy)
    return PolicyRead.model_validate(updated)


@router.post("/{policy_id}/cancel", response_model=PolicyRead)
async def cancel_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PolicyRead:
    """Cancel an existing policy."""
    policy = await PolicyService.get_policy(db, str(policy_id))
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="policy not found"
        )
    try:
        updated = await PolicyService.cancel_policy(db, policy)
    except PolicyServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return PolicyRead.model_validate(updated)


@router.post("/{policy_id}/renew", response_model=PolicyResponse)
async def renew_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    """Renew an existing policy by creating a linked next-cycle policy."""
    policy = await PolicyService.get_policy(db, str(policy_id))
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="policy not found"
        )
    try:
        new_policy, premium = await PolicyService.renew_policy(db, policy)
    except PolicyServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _to_policy_response(new_policy, premium)


@router.get("/{policy_id}", response_model=PolicyRead)
async def get_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PolicyRead:
    """Fetch full policy details by policy id."""
    policy = await PolicyService.get_policy(db, str(policy_id))
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="policy not found"
        )
    return PolicyRead.model_validate(policy)
