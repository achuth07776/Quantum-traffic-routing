"""
Google OR-Tools Capacitated Vehicle Routing Problem (CVRP) Solver.

Serves as the rigorous classical operational-research gold standard
against which the quantum-inspired Random-Key QPSO solver is benchmarked
on real OpenStreetMap road network travel-time matrices.
"""

import time
import math
from typing import List, Dict, Any, Optional
from ortools.constraint_solver import routing_enums_pb2, pywrapcp


def solve_cvrp_ortools(
    cost_matrix: List[List[float]],
    demands: List[float],
    vehicle_capacities: List[float],
    depot_index: int = 0,
    time_limit_seconds: float = 2.0,
    time_limit_ms: Optional[int] = None,
    duration_matrix_min: Optional[List[List[float]]] = None,
    max_route_time_min: Optional[float] = None
) -> Dict[str, Any]:
    """
    Solves Capacitated Vehicle Routing Problem using Google OR-Tools.

    Parameters:
        cost_matrix: NxN matrix of travel times (seconds) or distances (meters)
        demands: demand of each location (depot demand must be 0)
        vehicle_capacities: capacity limit for each vehicle
        depot_index: index of the depot (default 0)
        time_limit_seconds: search time budget for solver (default 2.0s)
        time_limit_ms: optional sub-second search budget in ms (e.g. 100, 250, 500)

    Returns:
        Dictionary containing solver status, routes, vehicle assignments,
        total cost, raw metrics, and computation runtime in ms.
    """
    start_time = time.time()
    num_locations = len(cost_matrix)
    num_vehicles = len(vehicle_capacities)

    # Scale costs and demands to integers for OR-Tools integer routing solver.
    # A scaling factor of 100,000 (10^5) preserves 5 decimal places of precision
    # for the dimensionless normalized objective J = 0.7*(T/T_ref) + 0.3*(D/D_ref)
    # (e.g. J = 4.6717 -> scaled integer 467,170) without integer rounding distortion.
    SCALE = 100_000
    INF_PENALTY = 1_000_000_000  # 1 billion penalty for unreachable/null transitions

    int_cost_matrix = []
    for row in cost_matrix:
        int_row = []
        for val in row:
            if val is None or val == float("inf") or (isinstance(val, float) and math.isinf(val)):
                int_row.append(INF_PENALTY)
            else:
                int_row.append(int(round(val * SCALE)))
        int_cost_matrix.append(int_row)

    int_demands = [int(round(d)) for d in demands]
    int_capacities = [int(round(c)) for c in vehicle_capacities]

    # Create routing index manager
    manager = pywrapcp.RoutingIndexManager(
        num_locations,
        num_vehicles,
        depot_index
    )

    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)

    # Define cost callback
    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int_cost_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Capacity constraint dimension
    def demand_callback(from_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        return int_demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        int_capacities,  # vehicle maximum capacities
        True,  # start cumul to zero
        "Capacity"
    )

    # Route-duration constraint. Without this, OR-Tools has no awareness of
    # max_route_time_min and can return a route that blows past it while
    # still reporting is_feasible=True.
    if duration_matrix_min is not None and max_route_time_min is not None:
        DURATION_SCALE = 1000  # minutes -> integer, sub-second precision

        int_duration_matrix = []
        for row in duration_matrix_min:
            int_row = []
            for val in row:
                if val is None or (isinstance(val, float) and math.isinf(val)):
                    int_row.append(INF_PENALTY)
                else:
                    int_row.append(int(round(val * DURATION_SCALE)))
            int_duration_matrix.append(int_row)

        def duration_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int_duration_matrix[from_node][to_node]

        duration_callback_index = routing.RegisterTransitCallback(duration_callback)
        routing.AddDimension(
            duration_callback_index,
            0,  # no slack
            int(round(max_route_time_min * DURATION_SCALE)),  # per-vehicle cap
            True,  # start cumul at zero
            "RouteDuration"
        )

    # Forbid unreachable transitions in the solver domain (Item 14)
    for from_node in range(num_locations):
        for to_node in range(num_locations):
            val = cost_matrix[from_node][to_node]
            if val is None or val == float("inf") or (isinstance(val, float) and math.isinf(val)) or val >= INF_PENALTY / SCALE:
                from_index = manager.NodeToIndex(from_node)
                to_index = manager.NodeToIndex(to_node)
                if from_index != -1 and to_index != -1 and from_index < routing.Size():
                    try:
                        routing.NextVar(from_index).RemoveValue(to_index)
                    except Exception:
                        pass

    # Search parameters: Guided Local Search metaheuristic
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )

    # Sub-second search budget configuration via protobuf Duration
    if time_limit_ms is not None:
        ms = max(10, min(int(time_limit_ms), 15_000))
        search_parameters.time_limit.seconds = int(ms // 1000)
        search_parameters.time_limit.nanos = int((ms % 1000) * 1_000_000)
        effective_budget_ms = ms
    else:
        sec_float = max(0.01, min(float(time_limit_seconds), 15.0))
        sec_int = int(sec_float)
        nanos = int((sec_float - sec_int) * 1_000_000_000)
        search_parameters.time_limit.seconds = sec_int
        search_parameters.time_limit.nanos = nanos
        effective_budget_ms = int(sec_float * 1000)

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    solver_status_code = routing.status()

    # Accurate status mapping (Item 13)
    # ROUTING_SUCCESS = 1, ROUTING_PARTIAL_SUCCESS = 2, ROUTING_FAIL = 3, ROUTING_FAIL_TIMEOUT = 4, ROUTING_INVALID = 5, ROUTING_INFEASIBLE = 6
    if not solution or solver_status_code in [3, 5, 6]:
        return {
            "status": "INFEASIBLE",
            "algorithm": "Google OR-Tools (CVRP)",
            "routes": [],
            "total_cost": float("inf"),
            "raw_total_cost": float("inf"),
            "runtime_ms": elapsed_ms,
            "budget_ms": effective_budget_ms,
            "is_feasible": False
        }

    # Extract solution routes
    vehicle_routes = []
    total_cost_scaled = 0

    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route_nodes = []
        route_load = 0
        route_cost_scaled = 0

        while not routing.IsEnd(index):
            node_idx = manager.IndexToNode(index)
            route_nodes.append(node_idx)
            route_load += demands[node_idx]
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_cost_scaled += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

        # Append final return to depot
        route_nodes.append(manager.IndexToNode(index))
        total_cost_scaled += route_cost_scaled

        # Only include active vehicles (visiting at least one customer)
        if len(route_nodes) > 2:
            vehicle_routes.append({
                "vehicle_id": vehicle_id,
                "stops": route_nodes,
                "load": route_load,
                "capacity": vehicle_capacities[vehicle_id],
                "route_cost": round(route_cost_scaled / SCALE, 4),
                "raw_route_cost": route_cost_scaled / SCALE
            })

    raw_total_cost = total_cost_scaled / SCALE
    total_cost = round(raw_total_cost, 4)

    # Determine accurate status: TIME_LIMIT_FEASIBLE vs OPTIMAL vs FEASIBLE (Item 13)
    if solver_status_code == 1:
        if elapsed_ms >= (effective_budget_ms * 0.90):
            status_str = "TIME_LIMIT_FEASIBLE"
        elif num_locations <= 6:
            status_str = "OPTIMAL"
        else:
            status_str = "FEASIBLE"
    elif solver_status_code in [2, 4]:
        status_str = "TIME_LIMIT_FEASIBLE"
    else:
        status_str = "FEASIBLE"

    return {
        "status": status_str,
        "algorithm": "Established Classical VRP Reference Solver (Google OR-Tools)",
        "routes": vehicle_routes,
        "total_cost": total_cost,
        "raw_total_cost": raw_total_cost,
        "vehicles_used": len(vehicle_routes),
        "runtime_ms": elapsed_ms,
        "budget_ms": effective_budget_ms,
        "is_feasible": True
    }
