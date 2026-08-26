import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.constants import OSRM_TIMEOUT_S, WALKING_DISTANCE_CACHE_TTL_S


@dataclass
class OSRMResult:
    distance_m: float
    duration_s: float


class OSRMClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: dict[str, tuple[OSRMResult, float]] = {}
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=OSRM_TIMEOUT_S)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _is_cache_valid(self, timestamp: float) -> bool:
        return (time.time() - timestamp) < WALKING_DISTANCE_CACHE_TTL_S

    def _cache_key(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> str:
        return f"{from_lat:.6f},{from_lon:.6f};{to_lat:.6f},{to_lon:.6f}"

    async def walking_distance(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> Optional[OSRMResult]:
        cache_key = self._cache_key(from_lat, from_lon, to_lat, to_lon)
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                return result

        client = await self._get_client()
        coords = f"{from_lon},{from_lat};{to_lon},{to_lat}"
        url = f"{settings.OSRM_BASE_URL}/route/v1/foot/{coords}"
        params = {"overview": "false", "geometries": "geojson"}

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok" or not data.get("routes"):
                return None

            route = data["routes"][0]
            distance_m = route.get("distance", 0)
            duration_s = route.get("duration", 0)

            if distance_m <= 0:
                return None

            result = OSRMResult(distance_m=distance_m, duration_s=duration_s)
            self._cache[cache_key] = (result, time.time())
            return result

        except httpx.HTTPError:
            return None
        except (KeyError, ValueError, IndexError):
            return None


_osrm_client: Optional[OSRMClient] = None


async def get_osrm_client() -> OSRMClient:
    global _osrm_client
    if _osrm_client is None:
        _osrm_client = OSRMClient()
    return _osrm_client


async def close_osrm_client():
    global _osrm_client
    if _osrm_client:
        await _osrm_client.close()
        _osrm_client = None