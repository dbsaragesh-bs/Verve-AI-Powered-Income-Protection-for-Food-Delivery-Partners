import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.claim import ClaimStatus, FraudTier
from app.models.event import Event
from app.schemas.claim import (
    ClaimListResponse,
    ClaimPipelineSummary,
    ClaimRead,
    ClaimReviewRequest,
    ClaimTriggerEvaluationRequest,
)
from app.services.claims_pipeline import (
    ClaimsPipeline,
    ClaimsPipelineError,
    evaluate_event,
)
from app.services.event_detection import scan_for_events

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("/trigger-evaluation", response_model=ClaimPipelineSummary)
async def trigger_evaluation(
    payload: ClaimTriggerEvaluationRequest,
    db: AsyncSession = Depends(get_db),
) -> ClaimPipelineSummary:
    """Trigger claims evaluation for an event id or by first triggering a simulation scenario."""
    if payload.event_id is None and not payload.scenario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either event_id or scenario",
        )

    if payload.scenario:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    f"{settings.sim_weather_url}/sim/orchestrator/trigger-scenario",
                    json={"scenario": payload.scenario, "time_compression": 10},
                )
                response.raise_for_status()
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"failed to trigger scenario: {exc}",
                ) from exc
        await asyncio.sleep(5)
        events = await scan_for_events(db, run_evaluation=False)
        if not events:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="no event detected for scenario",
            )
        summary = await evaluate_event(events[0].id, db)
        return ClaimPipelineSummary(**summary)

    event = await db.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="event not found"
        )

    summary = await evaluate_event(event.id, db)
    return ClaimPipelineSummary(**summary)


@router.get("", response_model=ClaimListResponse)
async def list_claims(
    status_filter: ClaimStatus | None = Query(default=None, alias="status"),
    worker_id: uuid.UUID | None = Query(default=None),
    event_id: uuid.UUID | None = Query(default=None),
    fraud_tier: FraudTier | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ClaimListResponse:
    """Return paginated claims list with filters by status/worker/event/fraud tier."""
    claims, total = await ClaimsPipeline.list_claims(
        session=db,
        status=status_filter,
        worker_id=worker_id,
        event_id=event_id,
        fraud_tier=fraud_tier,
        page=page,
        limit=limit,
    )
    return ClaimListResponse(
        page=page,
        limit=limit,
        total=total,
        items=[ClaimRead.model_validate(claim) for claim in claims],
    )


@router.get("/{claim_id}", response_model=ClaimRead)
async def get_claim(
    claim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ClaimRead:
    """Fetch full claim detail including all payout and fraud calculation fields."""
    claim = await ClaimsPipeline.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="claim not found"
        )
    return ClaimRead.model_validate(claim)


@router.post("/{claim_id}/review", response_model=ClaimRead)
async def review_claim(
    claim_id: uuid.UUID,
    payload: ClaimReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> ClaimRead:
    """Review under-review/provisional claims and finalize with approve or reject decision."""
    claim = await ClaimsPipeline.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="claim not found"
        )

    try:
        updated = await ClaimsPipeline.review_claim(
            session=db,
            claim=claim,
            decision=payload.decision,
            reviewer_notes=payload.reviewer_notes,
        )
    except ClaimsPipelineError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ClaimRead.model_validate(updated)
