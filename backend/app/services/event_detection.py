import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.event import Event
from app.services.claims_pipeline import evaluate_event
from app.services.premium_service import PremiumService

logger = logging.getLogger(__name__)


class EventDetectionServiceError(Exception):
    pass


def classify_weather_event(
    weather: dict[str, Any], zone_meta: dict[str, Any]
) -> dict[str, Any]:
    rainfall = float(weather.get("rainfall_mm_hr", 0) or 0)
    heat_index = float(weather.get("heat_index", 35) or 35)
    aqi = float(weather.get("aqi", 80) or 80)
    base_risk = float(zone_meta.get("base_risk", 0.25) or 0.25)

    if rainfall > 30:
        if base_risk > 0.5:
            return {"event_type": "FLOODING", "severity": "extreme", "confidence": 0.9}
        return {
            "event_type": "HEAVY_RAINFALL",
            "severity": "severe",
            "confidence": 0.88,
        }
    if rainfall > 15:
        return {
            "event_type": "HEAVY_RAINFALL",
            "severity": "moderate",
            "confidence": 0.75,
        }
    if heat_index > 42:
        return {"event_type": "EXTREME_HEAT", "severity": "severe", "confidence": 0.85}
    if aqi > 300:
        return {"event_type": "SEVERE_AQI", "severity": "severe", "confidence": 0.82}
    return {"event_type": "NONE", "severity": "none", "confidence": 0.0}


def _traffic_confirms(traffic_data: dict[str, Any]) -> bool:
    speed = float(traffic_data.get("avg_speed_kmh", 999) or 999)
    congestion = float(traffic_data.get("congestion_level", 0) or 0)
    return speed < 15 or congestion > 0.6


def _social_traffic_confirms(traffic_data: dict[str, Any]) -> bool:
    speed = float(traffic_data.get("avg_speed_kmh", 999) or 999)
    return speed < 10


def _platform_confirms(platform_data: dict[str, Any]) -> bool:
    current_volume = float(platform_data.get("order_volume", 0) or 0)
    average = float(platform_data.get("avg_orders_per_hour", 1) or 1)
    if average <= 0:
        return False
    return current_volume < (0.6 * average)


async def _safe_get(
    client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.warning("API call failed url=%s params=%s err=%s", url, params, exc)
        return {}


async def _safe_post(
    client: httpx.AsyncClient, url: str, payload: dict[str, Any]
) -> dict[str, Any]:
    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.warning("API post failed url=%s payload=%s err=%s", url, payload, exc)
        return {}


class EventDetectionService:
    @staticmethod
    async def _next_compound_id(db: AsyncSession) -> str:
        result = await db.execute(
            select(Event).order_by(Event.created_at.desc()).limit(1)
        )
        latest = result.scalar_one_or_none()
        sequence = 1
        if latest and latest.compound_event_id:
            try:
                sequence = int(latest.compound_event_id.split("_")[-1]) + 1
            except Exception:
                sequence = 1
        return f"EVT_2024_BLR_{sequence:04d}"

    @staticmethod
    async def _find_near_duplicate(
        db: AsyncSession,
        event_type: str,
        affected_zones: list[str],
    ) -> Event | None:
        cutoff = datetime.now() - timedelta(hours=2)
        result = await db.execute(
            select(Event)
            .where(Event.event_type == event_type, Event.created_at >= cutoff)
            .order_by(Event.created_at.desc())
        )
        candidates = list(result.scalars().all())
        affected_set = set(affected_zones)
        for candidate in candidates:
            zones = candidate.affected_zones or []
            if affected_set.intersection(zones):
                return candidate
        return None

    @staticmethod
    async def _fetch_zone_data(client: httpx.AsyncClient, zone: str) -> dict[str, Any]:
        platform_data = await _safe_get(
            client,
            f"{settings.sim_platform_url}/sim/platform/zone-activity",
            params={"zone": zone},
        )
        return platform_data

    @staticmethod
    async def _create_event(
        db: AsyncSession,
        event_type: str,
        severity: str,
        confidence: float,
        affected_zones: list[str],
        signal_sources: list[str],
        weather_data: dict[str, Any] | None = None,
        traffic_data: dict[str, Any] | None = None,
        platform_data: dict[str, Any] | None = None,
        social_data: dict[str, Any] | None = None,
    ) -> Event | None:
        duplicate = await EventDetectionService._find_near_duplicate(
            db, event_type, affected_zones
        )
        if duplicate is not None:
            duplicate.lifecycle_phase = "active"
            await db.commit()
            logger.info(
                "Duplicate event detected, lifecycle updated event_id=%s", duplicate.id
            )
            return None

        compound_event_id = await EventDetectionService._next_compound_id(db)
        existing = await db.scalar(
            select(Event).where(Event.compound_event_id == compound_event_id)
        )
        if existing is not None:
            logger.info(
                "Compound event id already exists, skipping id=%s", compound_event_id
            )
            return None

        event = Event(
            compound_event_id=compound_event_id,
            event_type=event_type,
            severity=severity,
            confidence=Decimal(str(confidence)).quantize(Decimal("0.01")),
            affected_zones=affected_zones,
            signal_sources=signal_sources,
            onset_time=datetime.now(),
            lifecycle_phase="onset",
            weather_data=weather_data,
            traffic_data=traffic_data,
            platform_data=platform_data,
            social_data=social_data,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event


async def scan_for_events(db: AsyncSession, run_evaluation: bool = True) -> list[Event]:
    logger.info("Starting event scan")
    new_events: list[Event] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        weather_payload = await _safe_get(
            client, f"{settings.sim_weather_url}/sim/weather/current-all"
        )
        traffic_payload = await _safe_get(
            client, f"{settings.sim_traffic_url}/sim/traffic/current-all"
        )
        social_payload = await _safe_get(
            client,
            f"{settings.sim_social_url}/sim/social/events",
            params={"city": "bengaluru"},
        )

        weather_zones = (
            weather_payload.get("zones", {})
            if isinstance(weather_payload, dict)
            else {}
        )
        traffic_zones = (
            traffic_payload.get("zones", {})
            if isinstance(traffic_payload, dict)
            else {}
        )

        for zone, weather in weather_zones.items():
            zone_meta = PremiumService.ZONES_META.get(
                zone, {"base_risk": Decimal("0.25")}
            )
            event_prediction = classify_weather_event(weather or {}, zone_meta)
            if event_prediction["event_type"] == "NONE":
                continue

            traffic_data = traffic_zones.get(zone, {})
            platform_data = await EventDetectionService._fetch_zone_data(client, zone)

            secondary_confirmed = _traffic_confirms(traffic_data) or _platform_confirms(
                platform_data
            )
            if not secondary_confirmed:
                logger.info(
                    "Weather event not confirmed by secondary signal zone=%s", zone
                )
                continue

            event = await EventDetectionService._create_event(
                db=db,
                event_type=event_prediction["event_type"],
                severity=event_prediction["severity"],
                confidence=event_prediction["confidence"],
                affected_zones=[zone],
                signal_sources=[
                    "weather",
                    "traffic" if _traffic_confirms(traffic_data) else "platform",
                ],
                weather_data=weather,
                traffic_data=traffic_data,
                platform_data=platform_data,
            )
            if event is not None:
                new_events.append(event)
                logger.info(
                    "New weather event created event_id=%s type=%s",
                    event.id,
                    event.event_type,
                )

        social_events = (
            social_payload.get("events", []) if isinstance(social_payload, dict) else []
        )
        for social_event in social_events:
            confidence = float(social_event.get("confidence", 0) or 0)
            if confidence <= 0.7:
                continue
            event_type = str(social_event.get("event_type", "")).upper()
            affected_zones = social_event.get("affected_zones", []) or []
            if not affected_zones:
                continue

            confirmed_zones = []
            for zone in affected_zones:
                t = traffic_zones.get(zone, {})
                if _social_traffic_confirms(t):
                    confirmed_zones.append(zone)

            if not confirmed_zones:
                logger.info(
                    "Social event not traffic-confirmed event_type=%s", event_type
                )
                continue

            event = await EventDetectionService._create_event(
                db=db,
                event_type=event_type,
                severity=str(social_event.get("severity", "moderate")),
                confidence=confidence,
                affected_zones=confirmed_zones,
                signal_sources=["social", "traffic"],
                social_data=social_event,
                traffic_data={
                    zone: traffic_zones.get(zone, {}) for zone in confirmed_zones
                },
            )
            if event is not None:
                new_events.append(event)
                logger.info(
                    "New social event created event_id=%s type=%s",
                    event.id,
                    event.event_type,
                )

    if run_evaluation:
        for event in new_events:
            try:
                await evaluate_event(event.id, db)
            except Exception as exc:
                logger.exception(
                    "Event evaluation failed event_id=%s err=%s", event.id, exc
                )

    logger.info("Event scan complete new_events=%s", len(new_events))
    return new_events


async def start_event_scanner(db_session_factory) -> None:
    logger.info("Starting background event scanner loop")
    while True:
        try:
            async with db_session_factory() as session:
                await scan_for_events(session)
        except Exception as exc:
            logger.exception("Background scan_for_events failed err=%s", exc)
        await asyncio.sleep(10)


async def trigger_scenario_and_scan(
    db: AsyncSession,
    scenario: str,
    time_compression: int = 10,
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        await _safe_post(
            client,
            f"{settings.sim_weather_url}/sim/orchestrator/trigger-scenario",
            {"scenario": scenario, "time_compression": time_compression},
        )
        await asyncio.sleep(3)

    events = await scan_for_events(db)
    return [
        {
            "event_id": str(event.id),
            "compound_event_id": event.compound_event_id,
            "event_type": event.event_type,
            "severity": event.severity,
        }
        for event in events
    ]
