import time
from typing import List, Dict, Any, Tuple
from app.domain.graph import RoadGraph
from optimization.interfaces.optimizer import RoutingProblem
from optimization.baselines.dijkstra import DijkstraOptimizer
from optimization.vrp.vrp_models import VRPProblem, VRPResult, VehicleRoute

class VRPGraphHelper:
    """Helper for computing and caching shortest path traversals between VRP stops."""
    def __init__(self, graph: RoadGraph, weights: Dict[str, float]):
        self.graph = graph
        self.weights = weights
        self.dijkstra = DijkstraOptimizer()
        self.cache: Dict[Tuple[str, str], Tuple[List[str], Dict[str, Any]]] = {}

    def get_path_and_metrics(self, u: str, v: str) -> Tuple[List[str], Dict[str, Any]]:
        if (u, v) in self.cache:
            return self.cache[(u, v)]
            
        prob = RoutingProblem(origin=u, destination=v, weights=self.weights)
        res = self.dijkstra.solve(self.graph, prob)
        
        if res.is_feasible:
            result = (res.path, {
                "travel_time_min": res.travel_time_min,
                "distance_km": res.distance_km,
                "cost": res.cost,
                "is_feasible": True
            })
        else:
            result = ([], {
                "travel_time_min": float('inf'),
                "distance_km": 0.0,
                "cost": float('inf'),
                "is_feasible": False
            })
        self.cache[(u, v)] = result
        return result


class GreedyVRP:
    """Greedy Nearest-Neighbor heuristic reference baseline for VRP."""
    def solve(self, graph: RoadGraph, problem: VRPProblem) -> VRPResult:
        start_time = time.perf_counter()
        helper = VRPGraphHelper(graph, problem.weights)
        
        depot = problem.depot_node
        customers = {c.node_id: c for c in problem.customers}
        unvisited = set(customers.keys())
        
        routes: List[VehicleRoute] = []
        
        for v_id in range(problem.num_vehicles):
            if not unvisited:
                break
                
            curr_node = depot
            curr_load = 0.0
            curr_time = 0.0
            tw_penalty = 0.0
            route_customers = []
            full_path = [depot]
            total_dist = 0.0
            total_cost = 0.0
            
            while unvisited:
                # Find nearest feasible customer respecting capacity AND max_route_time_min
                best_cust = None
                best_time = float('inf')
                best_path = []
                best_metrics = None
                
                for c_node in unvisited:
                    c_obj = customers[c_node]
                    # Hard constraint 1: Capacity
                    if curr_load + c_obj.demand_kg > problem.vehicle_capacity_kg:
                        continue
                        
                    path, metrics = helper.get_path_and_metrics(curr_node, c_node)
                    if not metrics["is_feasible"]:
                        continue
                        
                    # Check return-to-depot feasibility and max route time
                    ret_path, ret_metrics = helper.get_path_and_metrics(c_node, depot)
                    if not ret_metrics["is_feasible"]:
                        continue
                        
                    projected_total_time = (
                        curr_time + metrics["travel_time_min"] + c_obj.service_duration_min + ret_metrics["travel_time_min"]
                    )
                    
                    # Hard constraint 2: Max shift duration
                    if projected_total_time > problem.max_route_time_min:
                        continue
                        
                    if metrics["travel_time_min"] < best_time:
                        best_time = metrics["travel_time_min"]
                        best_cust = c_node
                        best_path = path
                        best_metrics = metrics
                        
                if not best_cust:
                    break
                    
                unvisited.remove(best_cust)
                c_obj = customers[best_cust]
                
                # Soft constraint: time window lateness penalty
                arrival = curr_time + best_metrics["travel_time_min"]
                if arrival < c_obj.time_window_start_min:
                    curr_time = c_obj.time_window_start_min
                else:
                    curr_time = arrival
                    if arrival > c_obj.time_window_end_min:
                        tw_penalty += (arrival - c_obj.time_window_end_min) * 5.0
                        
                curr_time += c_obj.service_duration_min
                curr_load += c_obj.demand_kg
                total_dist += best_metrics["distance_km"]
                total_cost += best_metrics["cost"]
                full_path.extend(best_path[1:])
                route_customers.append(best_cust)
                curr_node = best_cust
                
            # Return to depot
            if route_customers:
                ret_path, ret_metrics = helper.get_path_and_metrics(curr_node, depot)
                if ret_metrics["is_feasible"]:
                    total_dist += ret_metrics["distance_km"]
                    curr_time += ret_metrics["travel_time_min"]
                    total_cost += ret_metrics["cost"]
                    full_path.extend(ret_path[1:])
                    
                total_route_cost = total_cost + tw_penalty
                
                routes.append(VehicleRoute(
                    vehicle_id=v_id + 1,
                    customer_nodes=route_customers,
                    full_path_nodes=full_path,
                    total_load_kg=curr_load,
                    total_travel_time_min=round(curr_time, 2),
                    total_distance_km=round(total_dist, 2),
                    total_cost=round(total_route_cost, 3),
                    time_window_penalties=round(tw_penalty, 2),
                    exceeds_max_route_time=curr_time > problem.max_route_time_min,
                    is_feasible=True
                ))
                
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        total_fleet_time = sum(r.total_travel_time_min for r in routes)
        total_fleet_dist = sum(r.total_distance_km for r in routes)
        total_fleet_cost = sum(r.total_cost for r in routes)
        
        all_served = len(unvisited) == 0
        all_time_valid = all(r.total_travel_time_min <= problem.max_route_time_min for r in routes)
        
        return VRPResult(
            algorithm_name="Greedy Nearest Neighbor (Reference Baseline)",
            routes=routes,
            total_fleet_time_min=round(total_fleet_time, 2),
            total_fleet_distance_km=round(total_fleet_dist, 2),
            total_fleet_cost=round(total_fleet_cost, 3),
            unserved_customers=list(unvisited),
            runtime_ms=round(elapsed_ms, 2),
            iterations=1,
            is_feasible=all_served and all_time_valid,
            constraint_status={
                "capacity_satisfied": all(r.total_load_kg <= problem.vehicle_capacity_kg for r in routes),
                "max_route_time_satisfied": all_time_valid,
                "all_customers_served": all_served,
                "soft_time_window_penalties": round(sum(r.time_window_penalties for r in routes), 2)
            },
            provenance={
                "road_network": "CURATED REAL GEOGRAPHY (Visakhapatnam Coordinates)",
                "traffic": "SIMULATED (BPR Engine)",
                "cost": "DERIVED",
                "optimization": "CLASSICAL BASELINE"
            }
        )
