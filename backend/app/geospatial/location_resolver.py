import re
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.stop import Stop
from app.geospatial.aliases import resolve_alias, get_landmark_coords, STOP_ALIASES
from app.geospatial.nominatim import get_nominatim_client
from app.geospatial.schemas import LocationCandidate, LocationResolutionResult, ISLAMABAD_BOUNDS
from app.core.constants import DEFAULT_WALKING_RADIUS_M


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _fuzzy_match_score(query: str, target: str) -> float:
    query_norm = _normalize(query)
    target_norm = _normalize(target)

    if query_norm == target_norm:
        return 1.0

    if query_norm in target_norm or target_norm in query_norm:
        shorter = min(len(query_norm), len(target_norm))
        longer = max(len(query_norm), len(target_norm))
        return 0.8 * (shorter / longer)

    dist = _levenshtein_distance(query_norm, target_norm)
    max_len = max(len(query_norm), len(target_norm))
    if max_len > 0:
        similarity = 1.0 - (dist / max_len)
        if similarity >= 0.6:
            return min(0.8, 0.7 * similarity + 0.15)

    query_words = set(query_norm.split())
    target_words = set(target_norm.split())
    if query_words and target_words:
        intersection = query_words & target_words
        union = query_words | target_words
        jaccard = len(intersection) / len(union)
        if jaccard > 0.4:
            return 0.6 * jaccard

    return 0.0


async def _resolve_exact_stop(session: AsyncSession, text: str) -> list[LocationCandidate]:
    normalized = _normalize(text)
    result = await session.execute(
        select(Stop).where(func.lower(Stop.name) == normalized)
    )
    stops = result.scalars().all()

    candidates = []
    for stop in stops:
        if stop.location is not None:
            from geoalchemy2.shape import to_shape
            point = to_shape(stop.location)
            candidates.append(
                LocationCandidate(
                    stop_id=stop.id,
                    name=stop.name,
                    lat=point.y,
                    lon=point.x,
                    match_confidence=1.0,
                    match_type="exact_stop",
                )
            )
    return candidates


async def _resolve_fuzzy_stop(session: AsyncSession, text: str) -> list[LocationCandidate]:
    normalized = _normalize(text)
    result = await session.execute(select(Stop).where(Stop.location.is_not(None)))
    stops = result.scalars().all()

    candidates = []
    for stop in stops:
        score = _fuzzy_match_score(text, stop.name)
        if score >= 0.6:
            from geoalchemy2.shape import to_shape
            point = to_shape(stop.location)
            candidates.append(
                LocationCandidate(
                    stop_id=stop.id,
                    name=stop.name,
                    lat=point.y,
                    lon=point.x,
                    match_confidence=score,
                    match_type="fuzzy_stop",
                )
            )

    candidates.sort(key=lambda c: c.match_confidence, reverse=True)
    return candidates[:5]


async def _resolve_alias(session: AsyncSession, text: str) -> list[LocationCandidate]:
    """Resolve a known alias to a real transit stop.

    ``STOP_ALIASES`` maps a canonical stop key (matching ``Stop.external_key``)
    to a list of alias strings a user might type (e.g. "pims" -> "pims_hospital").
    The canonical key must be looked up against the ``stops`` table itself -
    it is NOT a landmark. ``LANDMARK_ALIASES``/``get_landmark_coords`` is a
    separate, unrelated table of generic landmarks (malls, parks, sectors)
    and must not be used here.
    """
    stop_key = resolve_alias(text)
    if stop_key:
        result = await session.execute(
            select(Stop).where(Stop.external_key == stop_key)
        )
        stop = result.scalar_one_or_none()
        if stop is not None and stop.location is not None:
            from geoalchemy2.shape import to_shape

            point = to_shape(stop.location)
            lat, lon = point.y, point.x
            if (
                ISLAMABAD_BOUNDS["min_lat"] <= lat <= ISLAMABAD_BOUNDS["max_lat"]
                and ISLAMABAD_BOUNDS["min_lon"] <= lon <= ISLAMABAD_BOUNDS["max_lon"]
            ):
                return [
                    LocationCandidate(
                        stop_id=stop.id,
                        name=stop.name,
                        lat=lat,
                        lon=lon,
                        match_confidence=0.9,
                        match_type="fuzzy_stop",
                    )
                ]

    # Fall back to the generic landmark table (malls, parks, sectors, etc.)
    # for aliases that aren't tied to a specific transit stop.
    coords = get_landmark_coords(text)
    if not coords:
        return []

    lat, lon = coords
    if not (
        ISLAMABAD_BOUNDS["min_lat"] <= lat <= ISLAMABAD_BOUNDS["max_lat"]
        and ISLAMABAD_BOUNDS["min_lon"] <= lon <= ISLAMABAD_BOUNDS["max_lon"]
    ):
        return []

    return [
        LocationCandidate(
            stop_id=None,
            name=text,
            lat=lat,
            lon=lon,
            match_confidence=0.9,
            match_type="fuzzy_stop",
        )
    ]


async def _resolve_nominatim(text: str) -> list[LocationCandidate]:
    client = await get_nominatim_client()
    result = await client.geocode(text)

    if not result:
        return []

    return [
        LocationCandidate(
            stop_id=None,
            name=result.display_name,
            lat=result.lat,
            lon=result.lon,
            match_confidence=result.confidence,
            match_type="geocoded",
        )
    ]


def _deduplicate_candidates(candidates: list[LocationCandidate]) -> list[LocationCandidate]:
    seen = set()
    unique = []
    for c in candidates:
        key = (round(c.lat, 4), round(c.lon, 4))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _check_ambiguity(candidates: list[LocationCandidate]) -> bool:
    if len(candidates) < 2:
        return False

    top_confidences = [c.match_confidence for c in candidates[:3]]
    if len(top_confidences) >= 2:
        diff = abs(top_confidences[0] - top_confidences[1])
        if diff < 0.15 and top_confidences[0] > 0.6:
            return True
    return False


async def resolve_location(
    session: AsyncSession, text: str
) -> LocationResolutionResult:
    if not text or not text.strip():
        return LocationResolutionResult(candidates=[])

    all_candidates = []

    exact = await _resolve_exact_stop(session, text)
    all_candidates.extend(exact)

    if not exact:
        fuzzy = await _resolve_fuzzy_stop(session, text)
        all_candidates.extend(fuzzy)

        alias = await _resolve_alias(session, text)
        all_candidates.extend(alias)

        if not fuzzy and not alias:
            nominatim = await _resolve_nominatim(text)
            all_candidates.extend(nominatim)

    all_candidates = _deduplicate_candidates(all_candidates)

    if _check_ambiguity(all_candidates):
        pass

    return LocationResolutionResult(candidates=all_candidates)