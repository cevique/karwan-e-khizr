from typing import Literal

from app.routing.schemas import Journey
from app.core.constants import MAX_JOURNEY_CANDIDATES


def rank_journeys(
    journeys: list[Journey],
    objective: Literal["fastest", "fewest_transfers", "least_walking"],
) -> list[Journey]:
    if objective == "fastest":
        return sorted(journeys, key=lambda j: (j.total_duration_s, j.transfer_count, j.total_walk_m))
    elif objective == "fewest_transfers":
        return sorted(journeys, key=lambda j: (j.transfer_count, j.total_duration_s, j.total_walk_m))
    elif objective == "least_walking":
        return sorted(journeys, key=lambda j: (j.total_walk_m, j.total_duration_s, j.transfer_count))
    return journeys


def select_top_candidates(journeys: list[Journey], limit: int = MAX_JOURNEY_CANDIDATES) -> list[Journey]:
    return journeys[:limit]