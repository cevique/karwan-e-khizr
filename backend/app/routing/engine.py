from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.geospatial.service import GeospatialService, get_geospatial_service
from app.geospatial.schemas import LocationCandidate, LocationResolutionResult
from app.routing.graph import TransitGraphBuilder, TransitGraph
from app.routing.dijkstra import run_dijkstra
from app.routing.time_aware import TimeAwareRouter
from app.routing.filters import apply_filters
from app.routing.ranking import rank_journeys, select_top_candidates
from app.routing.schemas import (
    JourneySearchRequest,
    JourneySearchResponse,
    Journey,
    Leg,
    FareQuote,
    LocationResolved,
    AmbiguousLocationResponse,
    NoRouteFoundResponse,
)
from app.routing.objectives import EdgeWeights
from app.routing.graph import GraphEdge
from app.core.constants import DEFAULT_WALKING_RADIUS_M
from app.core.exceptions import AmbiguousLocationError, NoRouteFoundError
from app.ticketing.fares import FaresService


class JourneySearchEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.geospatial_service: GeospatialService | None = None
        self.graph: TransitGraphBuilder | None = None
        self.fares_service = FaresService(session)

    async def _get_geospatial_service(self) -> GeospatialService:
        if self.geospatial_service is None:
            self.geospatial_service = await get_geospatial_service(self.session)
        return self.geospatial_service

    async def search(
        self,
        origin: str,
        destination: str,
        objective: Literal["fastest", "fewest_transfers", "least_walking"] = "fastest",
        max_walk_m: float | None = None,
        max_transfers: int | None = None,
        departure_time: datetime | None = None,
    ) -> JourneySearchResponse | AmbiguousLocationResponse | NoRouteFoundResponse:
        geospatial = await self._get_geospatial_service()

        origin_result = await geospatial.resolve_location(origin)
        dest_result = await geospatial.resolve_location(destination)

        if not origin_result.candidates:
            return NoRouteFoundResponse(
                error="no_route_found",
                message=f"No location found for origin: {origin}"
            )
        if not dest_result.candidates:
            return NoRouteFoundResponse(
                error="no_route_found",
                message=f"No location found for destination: {destination}"
            )

        origin_candidate = self._select_best_candidate(origin_result)
        dest_candidate = self._select_best_candidate(dest_result)

        if self._is_ambiguous(origin_result):
            return AmbiguousLocationResponse(
                error="ambiguous_origin",
                candidates=[
                    LocationResolved(name=c.name, lat=c.lat, lon=c.lon)
                    for c in origin_result.candidates[:5]
                ],
            )
        if self._is_ambiguous(dest_result):
            return AmbiguousLocationResponse(
                error="ambiguous_destination",
                candidates=[
                    LocationResolved(name=c.name, lat=c.lat, lon=c.lon)
                    for c in dest_result.candidates[:5]
                ],
            )

        builder = TransitGraphBuilder(self.session)
        await builder.build()
        await builder.add_origin_destination(origin_candidate, dest_candidate)
        graph = builder.graph

        origin_id = graph.origin_node_id
        dest_id = graph.destination_node_id

        if origin_id is None or dest_id is None:
            return NoRouteFoundResponse(
                error="no_route_found",
                message="Could not connect origin/destination to transit network"
            )

        paths = []
        if departure_time is not None:
            time_router = TimeAwareRouter(self.session, graph)
            path, cost = await time_router.find_time_dependent_path(
                origin_id, dest_id, departure_time, objective
            )
            if path:
                paths.append((path, cost, objective))
        else:
            path, cost = run_dijkstra(graph, origin_id, dest_id, objective)
            if path:
                paths.append((path, cost, objective))

        for alt_objective in ["fastest", "fewest_transfers", "least_walking"]:
            if alt_objective == objective:
                continue
            if departure_time is not None:
                time_router = TimeAwareRouter(self.session, graph)
                path, cost = await time_router.find_time_dependent_path(
                    origin_id, dest_id, departure_time, alt_objective
                )
            else:
                path, cost = run_dijkstra(graph, origin_id, dest_id, alt_objective)
            if path:
                paths.append((path, cost, alt_objective))

        journeys = []
        for path_edges, cost, path_objective in paths:
            journey = await self._build_journey(
                graph, path_edges, cost, origin_candidate, dest_candidate, path_objective
            )
            if journey:
                journeys.append(journey)

        if not journeys:
            return NoRouteFoundResponse(
                error="no_route_found",
                message="No transit route found between the specified origin and destination."
            )

        journeys = apply_filters(journeys, max_walk_m, max_transfers)

        if not journeys:
            return NoRouteFoundResponse(
                error="no_route_found",
                message="No routes found matching the specified filters."
            )

        journeys = rank_journeys(journeys, objective)
        journeys = select_top_candidates(journeys)

        return JourneySearchResponse(
            journeys=journeys,
            origin_resolved=LocationResolved(
                name=origin_candidate.name, lat=origin_candidate.lat, lon=origin_candidate.lon
            ),
            destination_resolved=LocationResolved(
                name=dest_candidate.name, lat=dest_candidate.lat, lon=dest_candidate.lon
            ),
        )

    def _select_best_candidate(self, result: LocationResolutionResult) -> LocationCandidate:
        exact = [c for c in result.candidates if c.match_type == "exact_stop"]
        if exact:
            return max(exact, key=lambda c: c.match_confidence)
        fuzzy = [c for c in result.candidates if c.match_type == "fuzzy_stop"]
        if fuzzy:
            return max(fuzzy, key=lambda c: c.match_confidence)
        return max(result.candidates, key=lambda c: c.match_confidence)

    def _is_ambiguous(self, result: LocationResolutionResult) -> bool:
        if len(result.candidates) < 2:
            return False
        top = sorted(result.candidates, key=lambda c: c.match_confidence, reverse=True)[:2]
        diff = abs(top[0].match_confidence - top[1].match_confidence)
        return diff < 0.15 and top[0].match_confidence > 0.6

    async def _build_journey(
        self,
        graph: TransitGraph,
        path_edges: list[GraphEdge],
        cost: EdgeWeights,
        origin: LocationCandidate,
        destination: LocationCandidate,
        objective: Literal["fastest", "fewest_transfers", "least_walking"],
    ) -> Journey | None:
        legs = []
        current_time = datetime.now()
        total_walk_m = 0.0
        transfer_count = 0

        for i, edge in enumerate(path_edges):
            if edge.edge_type == "walk":
                from_node = graph.graph.nodes.get(edge.from_stop_id)
                to_node = graph.graph.nodes.get(edge.to_stop_id)
                if not from_node or not to_node:
                    continue

                leg = Leg(
                    type="walk",
                    route_id=None,
                    trip_id=None,
                    start_stop_id=edge.from_stop_id,
                    end_stop_id=edge.to_stop_id,
                    start_lat=from_node.lat,
                    start_lon=from_node.lon,
                    end_lat=to_node.lat,
                    end_lon=to_node.lon,
                    duration_s=int(edge.duration_s),
                    distance_m=edge.distance_m,
                    geometry=None,
                    departure_time=current_time,
                    arrival_time=current_time,
                )
                legs.append(leg)
                total_walk_m += edge.distance_m or 0
                current_time = leg.arrival_time or current_time

            elif edge.edge_type == "ride":
                from_node = graph.graph.nodes.get(edge.from_stop_id)
                to_node = graph.graph.nodes.get(edge.to_stop_id)
                if not from_node or not to_node:
                    continue

                leg = Leg(
                    type="ride",
                    route_id=edge.route_id,
                    trip_id=edge.trip_id,
                    start_stop_id=edge.from_stop_id,
                    end_stop_id=edge.to_stop_id,
                    start_lat=from_node.lat,
                    start_lon=from_node.lon,
                    end_lat=to_node.lat,
                    end_lon=to_node.lon,
                    duration_s=int(edge.duration_s),
                    distance_m=edge.distance_m,
                    geometry=None,
                    departure_time=current_time,
                    arrival_time=current_time,
                )
                legs.append(leg)
                current_time = leg.arrival_time or current_time

            elif edge.edge_type == "transfer":
                transfer_count += 1

        ride_legs = [l for l in legs if l.type == "ride"]
        fare = await self.fares_service.get_fare_quote(len(ride_legs))

        return Journey(
            legs=legs,
            total_duration_s=int(cost.duration_s),
            total_walk_m=total_walk_m,
            transfer_count=transfer_count,
            fare=fare,
        )


def get_journey_search_engine(session: AsyncSession):
    return JourneySearchEngine(session)