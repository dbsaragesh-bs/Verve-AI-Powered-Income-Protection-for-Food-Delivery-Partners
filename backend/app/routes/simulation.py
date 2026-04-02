from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.claim import ClaimPipelineSummary
from app.schemas.simulation import SimulationResetResponse, SimulationTriggerRequest
from uuid import UUID

from app.services.claims_pipeline import evaluate_event
from app.services.event_detection import scan_for_events, trigger_scenario_and_scan

import httpx

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/trigger")
async def trigger_simulation(
    payload: SimulationTriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a simulation scenario, detect events, and run full claims evaluation."""
    events = await trigger_scenario_and_scan(
        db=db,
        scenario=payload.scenario,
        time_compression=payload.time_compression,
    )

    summaries: list[ClaimPipelineSummary] = []
    for event in events:
        summary = await evaluate_event(event_id=UUID(event["event_id"]), db=db)
        summaries.append(ClaimPipelineSummary(**summary))

    return {
        "events_detected": events,
        "claims_summary": [item.model_dump() for item in summaries],
    }


@router.post("/reset", response_model=SimulationResetResponse)
async def reset_simulation() -> SimulationResetResponse:
    """Reset the simulation orchestrator state."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{settings.sim_weather_url}/sim/orchestrator/reset"
            )
            response.raise_for_status()
            return SimulationResetResponse(status="ok", detail="simulation reset")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
            ) from exc


@router.get("/status")
async def simulation_status() -> dict:
    """Fetch current simulation orchestrator status."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.sim_weather_url}/sim/orchestrator/status"
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
            ) from exc


@router.post("/scan-and-evaluate")
async def manual_scan_and_evaluate(db: AsyncSession = Depends(get_db)) -> dict:
    """Manually trigger event scan and evaluate all newly detected events."""
    events = await scan_for_events(db, run_evaluation=False)
    summaries = []
    for event in events:
        summaries.append(await evaluate_event(event.id, db))
    return {"events_detected": len(events), "claims_summary": summaries}
