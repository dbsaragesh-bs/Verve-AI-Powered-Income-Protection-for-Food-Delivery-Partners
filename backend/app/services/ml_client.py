from typing import Any

import httpx

from app.config import settings


class MLClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=10.0)

    async def fetch_simulation_signals(self) -> dict[str, Any]:
        weather, traffic, platform, social = await self._fetch_all()
        return {
            "weather": weather,
            "traffic": traffic,
            "platform": platform,
            "social": social,
        }

    async def _fetch_all(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        async with self._client as client:
            weather = await self._safe_get(client, settings.sim_weather_url)
            traffic = await self._safe_get(client, settings.sim_traffic_url)
            platform = await self._safe_get(client, settings.sim_platform_url)
            social = await self._safe_get(client, settings.sim_social_url)
            return weather, traffic, platform, social

    async def _safe_get(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {"status": "unavailable", "source": url}
