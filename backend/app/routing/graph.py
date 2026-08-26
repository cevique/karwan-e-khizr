from dataclasses import dataclass, field
from typing import Literal
from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape

from app.db.models.stop import Stop
from app.db.models.route import Route
from app.db.models.route_stop import RouteStop
from app.db.models.trip import Trip
from app.db.models.stop_time import StopTime
from app.geospatial.schemas import LocationCandidate
from app.core.constants import DEFAULT_WALKING_RADIUS_M
from app.geospatial.nearby import nearby_stops
from app.geospatial.walking import walking_distance


@dataclass
class GraphNode:
    stop_id: int
    name: str
    lat: float
    lon: float
    routes: set[int] = field(default_factory=set)


@dataclass
class GraphEdge:
    from_stop_id: int
    to_stop_id: int
    route_id: int | None
    trip_id: int | None
    distance_m: float
    duration_s: float
    edge_type: Literal["walk", "ride", "transfer"]
    route_type: str | None = None


@dataclass
class TransitGraph:
    nodes: dict[int, GraphNode] = field(default_factory=dict)
    edges: dict[int, list[GraphEdge]] = field(default_factory=lambda: defaultdict(list))
    origin_node_id: int | None = None
    destination_node_id: int | None = None

    def add_node(self, node: GraphNode) -> None:
        if node.stop_id not in self.nodes:
            self.nodes[node.stop_id] = node
        else:
            self.nodes[node.stop_id].routes.update(node.routes)

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges[edge.from_stop_id].append(edge)

    def get_neighbors(self, stop_id: int) -> list[GraphEdge]:
        return self.edges.get(stop_id, [])

    def clear_origin_destination(self) -> None:
        if self.origin_node_id and self.origin_node_id < 0:
            self.nodes.pop(self.origin_node_id, None)
            self.edges.pop(self.origin_node_id, None)
        if self.destination_node_id and self.destination_node_id < 0:
            self.nodes.pop(self.destination_node_id, None)
            self.edges.pop(self.destination_node_id, None)
        self.origin_node_id = None
        self.destination_node_id = None


class TransitGraphBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.graph = TransitGraph()

    async def build(self) -> TransitGraph:
        await self._load_stops()
        await self._load_riding_edges()
        await self._load_walking_transfer_edges()
        return self.graph

    async def _load_stops(self) -> None:
        result = await self.session.execute(
            select(Stop.id, Stop.name, Stop.location).where(Stop.location.is_not(None))
        )
        for stop_id, name, location in result.all():
            point = to_shape(location)
            node = GraphNode(
                stop_id=stop_id,
                name=name,
                lat=point.y,
                lon=point.x,
            )
            self.graph.add_node(node)

    async def _load_riding_edges(self) -> None:
        result = await self.session.execute(
            select(
                RouteStop.route_id,
                RouteStop.stop_id,
                RouteStop.sequence,
                Route.route_type,
            )
            .join(Route, RouteStop.route_id == Route.id)
            .order_by(RouteStop.route_id, RouteStop.sequence)
        )

        route_sequences: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
        for route_id, stop_id, sequence, route_type in result.all():
            route_sequences[route_id].append((stop_id, sequence, route_type))

        for route_id, stops in route_sequences.items():
            stops.sort(key=lambda x: x[1])
            for i in range(len(stops) - 1):
                from_stop_id, _, route_type = stops[i]
                to_stop_id, _, _ = stops[i + 1]

                from_node = self.graph.nodes.get(from_stop_id)
                to_node = self.graph.nodes.get(to_stop_id)
                if not from_node or not to_node:
                    continue

                from_node.routes.add(route_id)
                to_node.routes.add(route_id)

                walk_result = await walking_distance(
                    from_node.lat, from_node.lon, to_node.lat, to_node.lon
                )
                distance_m = walk_result.distance_m
                duration_s = walk_result.duration_s

                if route_type == "metro":
                    from app.core.constants import AVERAGE_METRO_SPEED_MPS
                    speed = AVERAGE_METRO_SPEED_MPS
                else:
                    from app.core.constants import AVERAGE_BUS_SPEED_MPS
                    speed = AVERAGE_BUS_SPEED_MPS

                ride_duration_s = distance_m / speed + 30

                edge = GraphEdge(
                    from_stop_id=from_stop_id,
                    to_stop_id=to_stop_id,
                    route_id=route_id,
                    trip_id=None,
                    distance_m=distance_m,
                    duration_s=ride_duration_s,
                    edge_type="ride",
                    route_type=route_type,
                )
                self.graph.add_edge(edge)

                reverse_edge = GraphEdge(
                    from_stop_id=to_stop_id,
                    to_stop_id=from_stop_id,
                    route_id=route_id,
                    trip_id=None,
                    distance_m=distance_m,
                    duration_s=ride_duration_s,
                    edge_type="ride",
                    route_type=route_type,
                )
                self.graph.add_edge(reverse_edge)

    async def _load_walking_transfer_edges(self) -> None:
        stop_ids = list(self.graph.nodes.keys())
        for stop_id in stop_ids:
            node = self.graph.nodes[stop_id]
            nearby = await nearby_stops(self.session, node.lat, node.lon, DEFAULT_WALKING_RADIUS_M)
            for nearby_stop in nearby:
                if nearby_stop.stop_id == stop_id:
                    continue
                if nearby_stop.stop_id not in self.graph.nodes:
                    continue

                walk_result = await walking_distance(
                    node.lat, node.lon, nearby_stop.lat, nearby_stop.lon
                )

                if walk_result.distance_m <= DEFAULT_WALKING_RADIUS_M:
                    edge = GraphEdge(
                        from_stop_id=stop_id,
                        to_stop_id=nearby_stop.stop_id,
                        route_id=None,
                        trip_id=None,
                        distance_m=walk_result.distance_m,
                        duration_s=walk_result.duration_s,
                        edge_type="transfer",
                    )
                    self.graph.add_edge(edge)

    async def add_origin_destination(
        self, origin: LocationCandidate, destination: LocationCandidate
    ) -> tuple[int, int]:
        self.graph.clear_origin_destination()

        origin_id = -1
        dest_id = -2

        origin_node = GraphNode(
            stop_id=origin_id,
            name=f"Origin: {origin.name}",
            lat=origin.lat,
            lon=origin.lon,
        )
        dest_node = GraphNode(
            stop_id=dest_id,
            name=f"Destination: {destination.name}",
            lat=destination.lat,
            lon=destination.lon,
        )
        self.graph.add_node(origin_node)
        self.graph.add_node(dest_node)

        nearby_origin = await nearby_stops(
            self.session, origin.lat, origin.lon, DEFAULT_WALKING_RADIUS_M
        )
        for nearby in nearby_origin:
            if nearby.stop_id not in self.graph.nodes:
                continue
            walk_result = await walking_distance(
                origin.lat, origin.lon, nearby.lat, nearby.lon
            )
            if walk_result.distance_m <= DEFAULT_WALKING_RADIUS_M:
                edge = GraphEdge(
                    from_stop_id=origin_id,
                    to_stop_id=nearby.stop_id,
                    route_id=None,
                    trip_id=None,
                    distance_m=walk_result.distance_m,
                    duration_s=walk_result.duration_s,
                    edge_type="walk",
                )
                self.graph.add_edge(edge)

        nearby_dest = await nearby_stops(
            self.session, destination.lat, destination.lon, DEFAULT_WALKING_RADIUS_M
        )
        for nearby in nearby_dest:
            if nearby.stop_id not in self.graph.nodes:
                continue
            walk_result = await walking_distance(
                nearby.lat, nearby.lon, destination.lat, destination.lon
            )
            if walk_result.distance_m <= DEFAULT_WALKING_RADIUS_M:
                edge = GraphEdge(
                    from_stop_id=nearby.stop_id,
                    to_stop_id=dest_id,
                    route_id=None,
                    trip_id=None,
                    distance_m=walk_result.distance_m,
                    duration_s=walk_result.duration_s,
                    edge_type="walk",
                )
                self.graph.add_edge(edge)

        self.graph.origin_node_id = origin_id
        self.graph.destination_node_id = dest_id

        return origin_id, dest_id