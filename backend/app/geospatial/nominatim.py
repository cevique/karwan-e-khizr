import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.constants import (
    NOMINATIM_TIMEOUT_S,
    NOMINATIM_RATE_LIMIT_DELAY_S,
    GEOCODE_CACHE_TTL_S,
)
from app.geospatial.schemas import ISLAMABAD_BOUNDS


@dataclass
class NominatimResult:
    lat: float
    lon: float
    display_name: str
    confidence: float
    source: str = "nominatim"


class NominatimClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: dict[str, tuple[NominatimResult, float]] = {}
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=NOMINATIM_TIMEOUT_S,
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _is_cache_valid(self, timestamp: float) -> bool:
        return (time.time() - timestamp) < GEOCODE_CACHE_TTL_S

    def _is_within_bounds(self, lat: float, lon: float) -> bool:
        return (
            ISLAMABAD_BOUNDS["min_lat"] <= lat <= ISLAMABAD_BOUNDS["max_lat"]
            and ISLAMABAD_BOUNDS["min_lon"] <= lon <= ISLAMABAD_BOUNDS["max_lon"]
        )

    async def _rate_limit(self):
        async with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < NOMINATIM_RATE_LIMIT_DELAY_S:
                await asyncio.sleep(NOMINATIM_RATE_LIMIT_DELAY_S - elapsed)
            self._last_request_time = time.time()

    async def geocode(self, query: str) -> Optional[NominatimResult]:
        cache_key = query.lower().strip()
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                return result

        await self._rate_limit()

        client = await self._get_client()
        params = {
            "q": query,
            "format": "json",
            "limit": 5,
            "addressdetails": 1,
            "bounded": 1,
            "viewbox": f"{ISLAMABAD_BOUNDS['min_lon']},{ISLAMABAD_BOUNDS['max_lat']},{ISLAMABAD_BOUNDS['max_lon']},{ISLAMABAD_BOUNDS['min_lat']}",
        }

        try:
            response = await client.get(
                f"{settings.NOMINATIM_BASE_URL}/search", params=params
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            for item in data:
                try:
                    lat = float(item["lat"])
                    lon = float(item["lon"])

                    if not self._is_within_bounds(lat, lon):
                        continue

                    confidence = self._calculate_confidence(item)
                    result = NominatimResult(
                        lat=lat,
                        lon=lon,
                        display_name=item.get("display_name", query),
                        confidence=confidence,
                    )
                    self._cache[cache_key] = (result, time.time())
                    return result
                except (KeyError, ValueError):
                    continue

            return None

        except httpx.HTTPError:
            return None

    def _calculate_confidence(self, item: dict) -> float:
        confidence = 0.5

        if item.get("type") in ("amenity", "station", "stop", "halt", "bus_stop"):
            confidence += 0.2
        elif item.get("type") in ("poi", "building", "landmark"):
            confidence += 0.1

        importance = item.get("importance", 0)
        if importance > 0.7:
            confidence += 0.2
        elif importance > 0.5:
            confidence += 0.1

        address = item.get("address", {})
        city = address.get("city", "").lower()
        if city in ("islamabad", "rawalpindi"):
            confidence += 0.1

        return min(confidence, 1.0)

    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        cache_key = f"rev:{lat:.6f},{lon:.6f}"
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                return result.display_name

        await self._rate_limit()

        client = await self._get_client()
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
        }

        try:
            response = await client.get(
                f"{settings.NOMINATIM_BASE_URL}/reverse", params=params
            )
            response.raise_for_status()
            data = response.json()

            display_name = data.get("display_name")
            if display_name:
                result = NominatimResult(
                    lat=lat,
                    lon=lon,
                    display_name=display_name,
                    confidence=0.8,
                )
                self._cache[cache_key] = (result, time.time())
                return display_name

            return None

        except httpx.HTTPError:
            return None


_nominatim_client: Optional[NominatimClient] = None


async def get_nominatim_client() -> NominatimClient:
    global _nominatim_client
    if _nominatim_client is None:
        _nominatim_client = NominatimClient()
    return _nominatim_client


async def close_nominatim_client():
    global _nominatim_client
    if _nominatim_client:
        await _nominatim_client.close()
        _nominatim_client = None