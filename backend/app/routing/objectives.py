from dataclasses import dataclass
from typing import Literal

from app.core.constants import (
    AVERAGE_BUS_SPEED_MPS,
    AVERAGE_METRO_SPEED_MPS,
    AVERAGE_WALKING_SPEED_MPS,
    DEFAULT_DWELL_TIME_S,
    DEFAULT_TRANSFER_PENALTY_S,
)


@dataclass(frozen=True)
class EdgeWeights:
    duration_s: float
    transfers: int
    walk_m: float


def walking_edge_weight(
    distance_m: float,
    objective: Literal["fastest", "fewest_transfers", "least_walking"],
) -> EdgeWeights:
    duration_s = distance_m / AVERAGE_WALKING_SPEED_MPS
    if objective == "fastest":
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=distance_m)
    elif objective == "fewest_transfers":
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=distance_m)
    elif objective == "least_walking":
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=distance_m * 1000.0)
    else:
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=distance_m)


def riding_edge_weight(
    distance_m: float,
    route_type: str,
    objective: Literal["fastest", "fewest_transfers", "least_walking"],
) -> EdgeWeights:
    if route_type == "metro":
        speed = AVERAGE_METRO_SPEED_MPS
    else:
        speed = AVERAGE_BUS_SPEED_MPS
    duration_s = distance_m / speed + DEFAULT_DWELL_TIME_S
    if objective == "fastest":
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=0.0)
    elif objective == "fewest_transfers":
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=0.0)
    elif objective == "least_walking":
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=0.0)
    else:
        return EdgeWeights(duration_s=duration_s, transfers=0, walk_m=0.0)


def transfer_edge_weight(
    objective: Literal["fastest", "fewest_transfers", "least_walking"],
) -> EdgeWeights:
    if objective == "fastest":
        return EdgeWeights(
            duration_s=DEFAULT_TRANSFER_PENALTY_S, transfers=1, walk_m=0.0
        )
    elif objective == "fewest_transfers":
        return EdgeWeights(
            duration_s=DEFAULT_TRANSFER_PENALTY_S, transfers=1, walk_m=0.0
        )
    elif objective == "least_walking":
        return EdgeWeights(
            duration_s=DEFAULT_TRANSFER_PENALTY_S, transfers=1, walk_m=0.0
        )
    else:
        return EdgeWeights(
            duration_s=DEFAULT_TRANSFER_PENALTY_S, transfers=1, walk_m=0.0
        )


def compare_objective(
    a: EdgeWeights,
    b: EdgeWeights,
    objective: Literal["fastest", "fewest_transfers", "least_walking"],
) -> int:
    if objective == "fastest":
        if a.duration_s != b.duration_s:
            return -1 if a.duration_s < b.duration_s else 1
        if a.transfers != b.transfers:
            return -1 if a.transfers < b.transfers else 1
        if a.walk_m != b.walk_m:
            return -1 if a.walk_m < b.walk_m else 1
        return 0
    elif objective == "fewest_transfers":
        if a.transfers != b.transfers:
            return -1 if a.transfers < b.transfers else 1
        if a.duration_s != b.duration_s:
            return -1 if a.duration_s < b.duration_s else 1
        if a.walk_m != b.walk_m:
            return -1 if a.walk_m < b.walk_m else 1
        return 0
    elif objective == "least_walking":
        if a.walk_m != b.walk_m:
            return -1 if a.walk_m < b.walk_m else 1
        if a.duration_s != b.duration_s:
            return -1 if a.duration_s < b.duration_s else 1
        if a.transfers != b.transfers:
            return -1 if a.transfers < b.transfers else 1
        return 0
    return 0