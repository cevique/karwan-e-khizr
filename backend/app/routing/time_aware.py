from datetime import datetime, timedelta
from typing import Literal
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.db.models.route import Route
from app.db.models.route_stop import RouteStop
from app.routing.graph import TransitGraph, GraphEdge, GraphNode
from app.routing.objectives import EdgeWeights


class TimeAwareRouter:
    def __init__(self, session: AsyncSession, graph: TransitGraph):
        self.session = session
        self.graph = graph
        self.trip_cache: dict[int, list[StopTime]] = {}
        self.route_trips_cache: dict[int, list[Trip]] = {}

    async def find_time_dependent_path(
        self,
        start_id: int,
        end_id: int,
        departure_time: datetime,
        objective: Literal["fastest", "fewest_transfers", "least_walking"],
    ) -> tuple[list[GraphEdge] | None, EdgeWeights | None]:
        await self._load_schedule_data()

        if not self._has_schedule_data(start_id, end_id):
            return None, None

        return await self._earliest_arrival_dijkstra(
            start_id, end_id, departure_time, objective
        )

    async def _load_schedule_data(self) -> None:
        result = await self.session.execute(
            select(Trip)
            .options(selectinload(Trip.stop_times).selectinload(StopTime.stop))
            .join(Route, Trip.route_id == Route.id)
            .where(Trip.status == "scheduled")
        )
        trips = result.scalars().all()

        for trip in trips:
            if trip.route_id not in self.route_trips_cache:
                self.route_trips_cache[trip.route_id] = []
            self.route_trips_cache[trip.route_id].append(trip)

            stop_times = sorted(trip.stop_times, key=lambda st: st.sequence)
            self.trip_cache[trip.id] = stop_times

    def _has_schedule_data(self, start_id: int, end_id: int) -> bool:
        start_routes = self.graph.nodes.get(start_id, GraphNode(stop_id=0, name="", lat=0, lon=0)).routes
        end_routes = self.graph.nodes.get(end_id, GraphNode(stop_id=0, name="", lat=0, lon=0)).routes

        for route_id in start_routes:
            if route_id in self.route_trips_cache:
                return True
        return False

    async def _earliest_arrival_dijkstra(
        self,
        start_id: int,
        end_id: int,
        departure_time: datetime,
        objective: Literal["fastest", "fewest_transfers", "least_walking"],
    ) -> tuple[list[GraphEdge] | None, EdgeWeights | None]:
        from app.routing.objectives import compare_objective

        dist: dict[tuple[int, datetime], EdgeWeights] = {}
        prev: dict[tuple[int, datetime], tuple[tuple[int, datetime] | None, GraphEdge | None]] = {}

        start_state = (start_id, departure_time)
        start_cost = EdgeWeights(duration_s=0.0, transfers=0, walk_m=0.0)
        dist[start_state] = start_cost
        prev[start_state] = (None, None)

        import heapq
        pq: list[tuple[EdgeWeights, int, datetime]] = [(start_cost, start_id, departure_time)]

        visited = set()

        while pq:
            current_cost, current_id, current_time = heapq.heappop(pq)
            current_state = (current_id, current_time)

            if current_state in visited:
                continue
            visited.add(current_state)

            if current_id == end_id:
                break

            for edge in self.graph.get_neighbors(current_id):
                neighbor_id = edge.to_stop_id

                next_time, edge_cost = self._calculate_edge_traversal(
                    edge, current_time, objective
                )
                if next_time is None:
                    continue

                next_state = (neighbor_id, next_time)
                if next_state in visited:
                    continue

                new_cost = EdgeWeights(
                    duration_s=current_cost.duration_s + edge_cost.duration_s,
                    transfers=current_cost.transfers + edge_cost.transfers,
                    walk_m=current_cost.walk_m + edge_cost.walk_m,
                )

                if next_state not in dist or compare_objective(new_cost, dist[next_state], objective) < 0:
                    dist[next_state] = new_cost
                    prev[next_state] = (current_state, edge)
                    heapq.heappush(pq, (new_cost, neighbor_id, next_time))

        best_end_state = None
        best_cost = None
        for (stop_id, _), cost in dist.items():
            if stop_id == end_id:
                if best_cost is None or compare_objective(cost, best_cost, objective) < 0:
                    best_cost = cost
                    best_end_state = (stop_id, _)

        if best_end_state is None:
            return None, None

        path_edges = []
        current = best_end_state
        while current != start_state:
            prev_state, edge = prev.get(current, (None, None))
            if edge is None:
                break
            path_edges.append(edge)
            current = prev_state

        path_edges.reverse()
        return path_edges, best_cost

    def _calculate_edge_traversal(
        self,
        edge: GraphEdge,
        current_time: datetime,
        objective: Literal["fastest", "fewest_transfers", "least_walking"],
    ) -> tuple[datetime | None, EdgeWeights]:
        from app.core.constants import DEFAULT_DWELL_TIME_S, DEFAULT_TRANSFER_PENALTY_S
        from app.routing.objectives import (
            walking_edge_weight,
            riding_edge_weight,
            transfer_edge_weight,
        )

        if edge.edge_type == "walk":
            walk_cost = walking_edge_weight(edge.distance_m, objective)
            arrival_time = current_time + timedelta(seconds=walk_cost.duration_s)
            return arrival_time, walk_cost

        elif edge.edge_type == "transfer":
            transfer_cost = transfer_edge_weight(objective)
            arrival_time = current_time + timedelta(seconds=transfer_cost.duration_s)
            return arrival_time, transfer_cost

        elif edge.edge_type == "ride" and edge.route_id is not None:
            trip = self._find_next_trip(edge.route_id, edge.from_stop_id, edge.to_stop_id, current_time)
            if trip is None:
                return None, EdgeWeights(0, 0, 0)

            stop_times = self.trip_cache.get(trip.id, [])
            from_st = next((st for st in stop_times if st.stop_id == edge.from_stop_id), None)
            to_st = next((st for st in stop_times if st.stop_id == edge.to_stop_id), None)

            if not from_st or not to_st:
                return None, EdgeWeights(0, 0, 0)

            trip_start = trip.scheduled_start_time
            dep_time = trip_start + timedelta(seconds=from_st.departure_offset_s)
            arr_time = trip_start + timedelta(seconds=to_st.arrival_offset_s)

            if dep_time < current_time:
                return None, EdgeWeights(0, 0, 0)

            wait_s = (dep_time - current_time).total_seconds()
            ride_s = (arr_time - dep_time).total_seconds()
            total_s = wait_s + ride_s

            ride_cost = riding_edge_weight(edge.distance_m, edge.route_type or "bus", objective)
            total_cost = EdgeWeights(
                duration_s=ride_cost.duration_s + wait_s,
                transfers=ride_cost.transfers,
                walk_m=ride_cost.walk_m,
            )

            return arr_time, total_cost

        return None, EdgeWeights(0, 0, 0)

    def _find_next_trip(
        self,
        route_id: int,
        from_stop_id: int,
        to_stop_id: int,
        after_time: datetime,
    ) -> Trip | None:
        trips = self.route_trips_cache.get(route_id, [])
        candidates = []

        for trip in trips:
            stop_times = self.trip_cache.get(trip.id, [])
            from_st = next((st for st in stop_times if st.stop_id == from_stop_id), None)
            to_st = next((st for st in stop_times if st.stop_id == to_stop_id), None)

            if not from_st or not to_st:
                continue
            if from_st.sequence >= to_st.sequence:
                continue

            trip_start = trip.scheduled_start_time
            dep_time = trip_start + timedelta(seconds=from_st.departure_offset_s)

            if dep_time >= after_time:
                candidates.append((dep_time, trip))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]