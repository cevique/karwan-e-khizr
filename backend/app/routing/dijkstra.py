import heapq
from dataclasses import dataclass, field
from typing import Literal

from app.routing.graph import TransitGraph, GraphEdge
from app.routing.objectives import EdgeWeights, compare_objective


@dataclass(order=True)
class DijkstraState:
    cost: EdgeWeights = field(compare=False)
    stop_id: int = field(compare=False)
    prev_stop_id: int | None = field(default=None, compare=False)
    prev_edge: GraphEdge | None = field(default=None, compare=False)


def run_dijkstra(
    graph: TransitGraph,
    start_id: int,
    end_id: int,
    objective: Literal["fastest", "fewest_transfers", "least_walking"],
) -> tuple[list[GraphEdge] | None, EdgeWeights | None]:
    if start_id not in graph.nodes or end_id not in graph.nodes:
        return None, None

    dist: dict[int, EdgeWeights] = {}
    prev: dict[int, tuple[int | None, GraphEdge | None]] = {}

    start_cost = EdgeWeights(duration_s=0.0, transfers=0, walk_m=0.0)
    dist[start_id] = start_cost
    prev[start_id] = (None, None)

    pq: list[DijkstraState] = [DijkstraState(cost=start_cost, stop_id=start_id)]

    visited = set()

    while pq:
        state = heapq.heappop(pq)
        current_id = state.stop_id
        current_cost = state.cost

        if current_id in visited:
            continue
        visited.add(current_id)

        if current_id == end_id:
            break

        for edge in graph.get_neighbors(current_id):
            neighbor_id = edge.to_stop_id
            if neighbor_id in visited:
                continue

            edge_cost = _edge_cost(edge, objective)
            new_cost = EdgeWeights(
                duration_s=current_cost.duration_s + edge_cost.duration_s,
                transfers=current_cost.transfers + edge_cost.transfers,
                walk_m=current_cost.walk_m + edge_cost.walk_m,
            )

            if neighbor_id not in dist or compare_objective(new_cost, dist[neighbor_id], objective) < 0:
                dist[neighbor_id] = new_cost
                prev[neighbor_id] = (current_id, edge)
                heapq.heappush(pq, DijkstraState(cost=new_cost, stop_id=neighbor_id))

    if end_id not in dist:
        return None, None

    path_edges = []
    current = end_id
    while current != start_id:
        prev_stop, edge = prev.get(current, (None, None))
        if edge is None:
            break
        path_edges.append(edge)
        current = prev_stop

    path_edges.reverse()
    return path_edges, dist[end_id]


def _edge_cost(
    edge: GraphEdge,
    objective: Literal["fastest", "fewest_transfers", "least_walking"],
) -> EdgeWeights:
    if edge.edge_type == "walk":
        from app.routing.objectives import walking_edge_weight
        return walking_edge_weight(edge.distance_m, objective)
    elif edge.edge_type == "ride":
        from app.routing.objectives import riding_edge_weight
        return riding_edge_weight(edge.distance_m, edge.route_type or "bus", objective)
    elif edge.edge_type == "transfer":
        from app.routing.objectives import transfer_edge_weight
        return transfer_edge_weight(objective)
    return EdgeWeights(duration_s=0.0, transfers=0, walk_m=0.0)