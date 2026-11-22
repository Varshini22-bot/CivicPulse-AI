import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Report
from app.services.duplicate_service import DuplicateService

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    ORTOOLS_AVAILABLE = True
except Exception:
    ORTOOLS_AVAILABLE = False


class RoutingService:
    """
    Municipal field crew dispatch route optimization using Google OR-Tools.
    Solves the Traveling Salesperson Problem (TSP) across open high-priority civic tickets,
    minimizing fuel consumption, crew transit time, and idle deadheading.
    """

    # Average municipal repair truck speed in urban Bengaluru: ~18 km/h (300 meters/min)
    TRUCK_METERS_PER_MINUTE = 300.0
    # Average inspection/triage dwell time per stop: 15 minutes
    SERVICE_DWELL_MINUTES = 15.0

    @classmethod
    def optimize_dispatch_route(
        cls,
        reports: List[Report],
        start_latitude: Optional[float] = None,
        start_longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Computes optimal sequence of stops for municipal repair crews.
        """
        if not reports:
            return {
                "total_stops": 0,
                "total_distance_km": 0.0,
                "estimated_transit_minutes": 0.0,
                "estimated_total_duration_minutes": 0.0,
                "ordered_stops": [],
                "optimization_algorithm": "none"
            }

        # If depot is not specified, use the highest priority ticket or centroid as start
        if start_latitude is None or start_longitude is None:
            sorted_by_priority = sorted(reports, key=lambda r: r.priority_score, reverse=True)
            depot_lat = sorted_by_priority[0].latitude
            depot_lon = sorted_by_priority[0].longitude
        else:
            depot_lat = start_latitude
            depot_lon = start_longitude

        # Waypoints: index 0 is Depot, indices 1..N are reports
        waypoints = [{"type": "depot", "title": "Municipal Operations Hub", "lat": depot_lat, "lon": depot_lon, "report": None}]
        for r in reports:
            waypoints.append({
                "type": "report",
                "title": r.title,
                "lat": r.latitude,
                "lon": r.longitude,
                "report": r
            })

        n_locations = len(waypoints)

        # Distance matrix in integer meters for OR-Tools
        dist_matrix = [[0] * n_locations for _ in range(n_locations)]
        for i in range(n_locations):
            for j in range(n_locations):
                if i != j:
                    d = DuplicateService.haversine_distance(
                        waypoints[i]["lat"], waypoints[i]["lon"],
                        waypoints[j]["lat"], waypoints[j]["lon"]
                    )
                    dist_matrix[i][j] = int(round(d))

        route_indices = []

        if ORTOOLS_AVAILABLE and n_locations > 2:
            try:
                manager = pywrapcp.RoutingIndexManager(n_locations, 1, 0)
                routing = pywrapcp.RoutingModel(manager)

                def distance_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    return dist_matrix[from_node][to_node]

                transit_callback_index = routing.RegisterTransitCallback(distance_callback)
                routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

                search_parameters = pywrapcp.DefaultRoutingSearchParameters()
                search_parameters.first_solution_strategy = (
                    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                )

                solution = routing.SolveWithParameters(search_parameters)
                if solution:
                    index = routing.Start(0)
                    while not routing.IsEnd(index):
                        node = manager.IndexToNode(index)
                        route_indices.append(node)
                        index = solution.Value(routing.NextVar(index))
            except Exception:
                route_indices = []

        # Fallback to nearest-neighbor greedy heuristic if OR-Tools unavailable or failed
        if not route_indices:
            visited = [False] * n_locations
            current = 0
            visited[0] = True
            route_indices = [0]
            for _ in range(n_locations - 1):
                best_next = None
                best_dist = float("inf")
                for candidate in range(n_locations):
                    if not visited[candidate] and dist_matrix[current][candidate] < best_dist:
                        best_dist = dist_matrix[current][candidate]
                        best_next = candidate
                if best_next is not None:
                    visited[best_next] = True
                    route_indices.append(best_next)
                    current = best_next

        # Build ordered stops payload
        ordered_stops = []
        cumulative_dist_m = 0.0

        for step_idx, node_idx in enumerate(route_indices):
            wp = waypoints[node_idx]
            prev_node = route_indices[step_idx - 1] if step_idx > 0 else node_idx
            leg_dist_m = dist_matrix[prev_node][node_idx] if step_idx > 0 else 0
            cumulative_dist_m += leg_dist_m

            r = wp["report"]
            ordered_stops.append({
                "stop_number": step_idx + 1,
                "location_type": wp["type"],
                "report_id": r.id if r else None,
                "tracking_number": r.tracking_number if r else "BBMP-HUB",
                "title": r.title if r else wp["title"],
                "category": r.category.name if (r and r.category) else "Operations",
                "priority_level": r.priority_level if r else "N/A",
                "priority_score": r.priority_score if r else 0.0,
                "latitude": wp["lat"],
                "longitude": wp["lon"],
                "address": r.address if r else "Municipal Ward Hub",
                "leg_distance_meters": leg_dist_m,
                "cumulative_distance_km": round(cumulative_dist_m / 1000.0, 2),
                "estimated_arrival_minutes": round(cumulative_dist_m / cls.TRUCK_METERS_PER_MINUTE + (step_idx * cls.SERVICE_DWELL_MINUTES), 1)
            })

        total_distance_km = round(cumulative_dist_m / 1000.0, 2)
        total_transit_mins = round(cumulative_dist_m / cls.TRUCK_METERS_PER_MINUTE, 1)
        total_service_mins = (len(reports)) * cls.SERVICE_DWELL_MINUTES
        total_duration_mins = round(total_transit_mins + total_service_mins, 1)

        return {
            "total_stops": len(ordered_stops),
            "total_inspections": len(reports),
            "total_distance_km": total_distance_km,
            "estimated_transit_minutes": total_transit_mins,
            "estimated_service_minutes": total_service_mins,
            "estimated_total_duration_minutes": total_duration_mins,
            "ordered_stops": ordered_stops,
            "optimization_algorithm": "google_ortools_tsp" if ORTOOLS_AVAILABLE else "greedy_nearest_neighbor"
        }
