from typing import Literal

from app.routing.schemas import Journey
from app.routing.graph import GraphEdge


def filter_by_max_walk(journeys: list[Journey], max_walk_m: float) -> list[Journey]:
    return [j for j in journeys if j.total_walk_m <= max_walk_m]


def filter_by_max_transfers(journeys: list[Journey], max_transfers: int) -> list[Journey]:
    return [j for j in journeys if j.transfer_count <= max_transfers]


def apply_filters(
    journeys: list[Journey],
    max_walk_m: float | None = None,
    max_transfers: int | None = None,
) -> list[Journey]:
    filtered = journeys
    if max_walk_m is not None:
        filtered = filter_by_max_walk(filtered, max_walk_m)
    if max_transfers is not None:
        filtered = filter_by_max_transfers(filtered, max_transfers)
    return filtered