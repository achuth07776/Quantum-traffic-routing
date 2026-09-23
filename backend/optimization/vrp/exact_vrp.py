import time
import itertools
from typing import List
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem, VRPResult, VehicleRoute, CustomerStop
from optimization.vrp.vrp_baselines import VRPGraphHelper

class ExactExhaustiveVRP:
    """
    Exact Exhaustive Permutation & Partition Solver for small VRP instances (N <= 8).
    Exhaustively evaluates all feasible customer permutations and vehicle partitions
    to guarantee the exact mathematical global minimum of the implemented objective.
    """
    def solve(self, graph: RoadGraph, problem: VRPProblem) -> VRPResult:
        start_time = time.perf_counter()
        helper = VRPGraphHelper(graph, problem.weights)
        
        customers = problem.customers
        num_cust = len(customers)
        depot = problem.depot_node
        
        if num_cust > 8:
            raise ValueError(f"ExactExhaustiveVRP is intended for N <= 8 customers, received N={num_cust}")
            
        best_cost = float('inf')
        best_routes: List[VehicleRoute] = []
        best_unserved: List[str] = []
        
        # Test all permutations of customer sequences
        for perm in itertools.permutations(customers):
            # Split permutation across num_vehicles (using combinations of divider bars)
            for dividers in itertools.combinations(range(num_cust + problem.num_vehicles - 1), problem.num_vehicles - 1):
                vehicle_subsets: List[List[CustomerStop]] = []
                last_div = -1
                item_idx = 0
                
                for div in list(dividers) + [num_cust + problem.num_vehicles - 1]:
                    num_items_in_vehicle = div - last_div - 1
                    vehicle_subsets.append(list(perm[item_idx : item_idx + num_items_in_vehicle]))
                    item_idx += num_items_in_vehicle
                    last_div = div
                    
                current_routes: List[VehicleRoute] = []
                solution_cost = 0.0
                is_valid = True
                
                for v_id, subset in enumerate(vehicle_subsets):
                    if not subset:
                        continue
                        
                    curr_node = depot
                    curr_load = 0.0
                    curr_time = 0.0
                    tw_penalty = 0.0
                    route_cost = 0.0
                    route_dist = 0.0
                    full_path = [depot]
                    route_cust_ids = []
                    
                    for c in subset:
                        # Hard Constraint 1: Capacity check
                        if curr_load + c.demand_kg > problem.vehicle_capacity_kg:
                            is_valid = False
                            break
                            
                        path, metrics = helper.get_path_and_metrics(curr_node, c.node_id)
                        if not metrics["is_feasible"]:
                            is_valid = False
                            break
                            
                        # Arrival and time window
                        arrival = curr_time + metrics["travel_time_min"]
                        if arrival < c.time_window_start_min:
                            curr_time = c.time_window_start_min
                        else:
                            curr_time = arrival
                            if arrival > c.time_window_end_min:
                                tw_penalty += (arrival - c.time_window_end_min) * 5.0
                                
                        curr_time += c.service_duration_min
                        curr_load += c.demand_kg
                        route_dist += metrics["distance_km"]
                        route_cost += metrics["cost"]
                        full_path.extend(path[1:])
                        route_cust_ids.append(c.node_id)
                        curr_node = c.node_id
                        
                    if not is_valid:
                        break
                        
                    # Return to depot
                    ret_path, ret_metrics = helper.get_path_and_metrics(curr_node, depot)
                    if not ret_metrics["is_feasible"]:
                        is_valid = False
                        break
                        
                    curr_time += ret_metrics["travel_time_min"]
                    route_dist += ret_metrics["distance_km"]
                    route_cost += ret_metrics["cost"]
                    full_path.extend(ret_path[1:])
                    
                    # Hard Constraint 2: Maximum route duration ceiling
                    if curr_time > problem.max_route_time_min:
                        is_valid = False
                        break
                        
                    total_route_cost = route_cost + tw_penalty
                    solution_cost += total_route_cost
                    
                    current_routes.append(VehicleRoute(
                        vehicle_id=v_id + 1,
                        customer_nodes=route_cust_ids,
                        full_path_nodes=full_path,
                        total_load_kg=curr_load,
                        total_travel_time_min=round(curr_time, 2),
                        total_distance_km=round(route_dist, 2),
                        total_cost=round(total_route_cost, 3),
                        time_window_penalties=round(tw_penalty, 2),
                        exceeds_max_route_time=False,
                        is_feasible=True
                    ))
                    
                if is_valid and solution_cost < best_cost:
                    best_cost = solution_cost
                    best_routes = current_routes
                    best_unserved = []
                    
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        total_time = sum(r.total_travel_time_min for r in best_routes)
        total_dist = sum(r.total_distance_km for r in best_routes)
        
        return VRPResult(
            algorithm_name="Exact Exhaustive Permutation Solver (Global Optimum)",
            routes=best_routes,
            total_fleet_time_min=round(total_time, 2),
            total_fleet_distance_km=round(total_dist, 2),
            total_fleet_cost=round(best_cost if best_cost < float('inf') else 0.0, 3),
            unserved_customers=best_unserved,
            optimality_gap_pct=0.0,
            runtime_ms=round(elapsed_ms, 2),
            iterations=1,
            is_feasible=best_cost < float('inf') and len(best_routes) > 0,
            constraint_status={
                "capacity_satisfied": True,
                "max_route_time_satisfied": True,
                "all_customers_served": True,
                "soft_time_window_penalties": round(sum(r.time_window_penalties for r in best_routes), 2)
            },
            provenance={
                "road_network": "CURATED REAL GEOGRAPHY (Visakhapatnam Coordinates)",
                "traffic": "SIMULATED (BPR Engine)",
                "cost": "DERIVED",
                "optimization": "EXACT GLOBAL OPTIMUM (EXHAUSTIVE SEARCH)"
            }
        )

# Alias for backward compatibility
ExactVRP = ExactExhaustiveVRP
