import time
import random
import numpy as np
from typing import List, Any, Optional, Tuple
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem, VRPResult, VehicleRoute
from optimization.vrp.vrp_baselines import VRPGraphHelper

class RandomKeyQPSOVRP:
    """
    Quantum-Behaved Particle Swarm Optimization (QPSO) with Random-Key Encoding
    and Capacity/Duration-Aware Sequential Decoding for Capacitated Vehicle Routing (CVRP) with Time Windows.
    
    Constraint Structure:
    - HARD: Vehicle capacity ceiling, maximum shift duration (max_route_time_min), valid contiguous road graph.
    - SOFT: Time-window lateness penalty.
    """
    def __init__(
        self,
        num_particles: int = 30,
        beta_max: float = 1.0,
        beta_min: float = 0.5,
        tw_penalty_weight: float = 5.0
    ):
        self.num_particles = num_particles
        self.beta_max = beta_max
        self.beta_min = beta_min
        self.tw_penalty_weight = tw_penalty_weight

    def _decode_and_repair(
        self,
        particle_keys: np.ndarray,
        problem: VRPProblem,
        helper: VRPGraphHelper
    ) -> Tuple[List[VehicleRoute], float, List[str]]:
        """
        Decodes continuous particle keys into customer sequence, assigns to vehicle routes
        strictly enforcing capacity & max_route_time_min, and adds soft time-window penalties.
        """
        customers = problem.customers
        num_cust = len(customers)
        depot = problem.depot_node
        
        # 1. Sort customer indices by particle key (Random-Key Decoder)
        sorted_indices = np.argsort(particle_keys)
        ordered_customers = [customers[idx] for idx in sorted_indices]
        
        vehicle_routes: List[VehicleRoute] = []
        unserved: List[str] = []
        
        curr_cust_idx = 0
        total_solution_cost = 0.0
        
        for v_id in range(problem.num_vehicles):
            if curr_cust_idx >= num_cust:
                break
                
            curr_node = depot
            curr_load = 0.0
            curr_time = 0.0
            tw_penalty = 0.0
            route_customers = []
            full_path = [depot]
            route_cost = 0.0
            route_dist = 0.0
            
            while curr_cust_idx < num_cust:
                c = ordered_customers[curr_cust_idx]
                
                # Hard constraint 1: Capacity check
                if curr_load + c.demand_kg > problem.vehicle_capacity_kg:
                    break  # Vehicle at capacity, dispatch next vehicle
                    
                path, metrics = helper.get_path_and_metrics(curr_node, c.node_id)
                if not metrics["is_feasible"]:
                    unserved.append(c.node_id)
                    curr_cust_idx += 1
                    continue
                    
                # Check return-to-depot feasibility and max route time ceiling
                ret_path, ret_metrics = helper.get_path_and_metrics(c.node_id, depot)
                if not ret_metrics["is_feasible"]:
                    unserved.append(c.node_id)
                    curr_cust_idx += 1
                    continue
                    
                # Arrival & service time
                arrival_time = curr_time + metrics["travel_time_min"]
                actual_start = max(arrival_time, c.time_window_start_min)
                departure_time = actual_start + c.service_duration_min
                projected_total_time = departure_time + ret_metrics["travel_time_min"]
                
                # Hard constraint 2: Max route time limit
                if projected_total_time > problem.max_route_time_min:
                    break  # Vehicle duration reached limit, dispatch next vehicle
                    
                # Soft constraint: Time window lateness penalty
                if arrival_time > c.time_window_end_min:
                    lateness = arrival_time - c.time_window_end_min
                    tw_penalty += lateness * self.tw_penalty_weight
                    
                curr_time = departure_time
                curr_load += c.demand_kg
                route_dist += metrics["distance_km"]
                route_cost += metrics["cost"]
                full_path.extend(path[1:])
                route_customers.append(c.node_id)
                curr_node = c.node_id
                curr_cust_idx += 1
                
            # Return to depot
            if route_customers:
                ret_path, ret_metrics = helper.get_path_and_metrics(curr_node, depot)
                if ret_metrics["is_feasible"]:
                    route_dist += ret_metrics["distance_km"]
                    route_cost += ret_metrics["cost"]
                    curr_time += ret_metrics["travel_time_min"]
                    full_path.extend(ret_path[1:])
                else:
                    route_cost += 1000.0  # Infeasible path penalty
                    
                total_route_cost = route_cost + tw_penalty
                total_solution_cost += total_route_cost
                
                vehicle_routes.append(VehicleRoute(
                    vehicle_id=v_id + 1,
                    customer_nodes=route_customers,
                    full_path_nodes=full_path,
                    total_load_kg=curr_load,
                    total_travel_time_min=round(curr_time, 2),
                    total_distance_km=round(route_dist, 2),
                    total_cost=round(total_route_cost, 3),
                    time_window_penalties=round(tw_penalty, 2),
                    exceeds_max_route_time=curr_time > problem.max_route_time_min,
                    is_feasible=len(route_customers) > 0 and curr_time <= problem.max_route_time_min
                ))
                
        # Unserved customers penalty
        while curr_cust_idx < num_cust:
            unserved.append(ordered_customers[curr_cust_idx].node_id)
            total_solution_cost += 2000.0
            curr_cust_idx += 1
            
        return vehicle_routes, total_solution_cost, unserved

    def solve(self, graph: Optional[RoadGraph], problem: VRPProblem, helper: Optional[Any] = None) -> VRPResult:
        start_time = time.perf_counter()
        
        if problem.seed is not None:
            random.seed(problem.seed)
            np.random.seed(problem.seed)
            
        if helper is None:
            helper = VRPGraphHelper(graph, problem.weights)
        num_cust = len(problem.customers)
        pop_size = max(10, min(self.num_particles, problem.population_size))
        max_iter = max(15, min(problem.max_iterations, 100))
        
        # Fresh swarm initialization per run (prevents stale pBest across scenario changes)
        particles = np.random.uniform(-1.0, 1.0, (pop_size, num_cust))
        pbest_positions = np.copy(particles)
        pbest_costs = np.full(pop_size, float('inf'))
        pbest_solutions = [None] * pop_size
        
        gbest_position = np.zeros(num_cust)
        gbest_cost = float('inf')
        gbest_routes: List[VehicleRoute] = []
        gbest_unserved: List[str] = []
        
        convergence_curve: List[float] = []
        
        # Initial evaluation
        for i in range(pop_size):
            routes, cost, unserved = self._decode_and_repair(particles[i], problem, helper)
            pbest_costs[i] = cost
            pbest_solutions[i] = (routes, unserved)
            if cost < gbest_cost:
                gbest_cost = cost
                gbest_position = np.copy(particles[i])
                gbest_routes = routes
                gbest_unserved = unserved
                
        # Main QPSO Loop
        for t in range(max_iter):
            beta = self.beta_max - (self.beta_max - self.beta_min) * (t / max_iter)
            mbest = np.mean(pbest_positions, axis=0)
            
            for i in range(pop_size):
                phi = np.random.uniform(0.0, 1.0, num_cust)
                p_attractor = phi * pbest_positions[i] + (1.0 - phi) * gbest_position
                
                u = np.random.uniform(0.0001, 0.9999, num_cust)
                sign = np.random.choice([-1.0, 1.0], size=num_cust)
                
                # Delta-potential well position update
                particles[i] = p_attractor + sign * beta * np.abs(mbest - particles[i]) * np.log(1.0 / u)
                particles[i] = np.clip(particles[i], -3.0, 3.0)
                
                routes, cost, unserved = self._decode_and_repair(particles[i], problem, helper)
                if cost < pbest_costs[i]:
                    pbest_costs[i] = cost
                    pbest_positions[i] = np.copy(particles[i])
                    pbest_solutions[i] = (routes, unserved)
                    
                    if cost < gbest_cost:
                        gbest_cost = cost
                        gbest_position = np.copy(particles[i])
                        gbest_routes = routes
                        gbest_unserved = unserved
                        
            convergence_curve.append(round(gbest_cost if gbest_cost < float('inf') else 0.0, 3))
            
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        total_fleet_time = sum(r.total_travel_time_min for r in gbest_routes)
        total_fleet_dist = sum(r.total_distance_km for r in gbest_routes)
        
        all_served = len(gbest_unserved) == 0
        all_time_valid = all(r.total_travel_time_min <= problem.max_route_time_min for r in gbest_routes)
        
        return VRPResult(
            algorithm_name="Random-Key QPSO (Quantum-Inspired)",
            routes=gbest_routes,
            total_fleet_time_min=round(total_fleet_time, 2),
            total_fleet_distance_km=round(total_fleet_dist, 2),
            total_fleet_cost=round(gbest_cost, 3),
            unserved_customers=gbest_unserved,
            runtime_ms=round(elapsed_ms, 2),
            iterations=max_iter,
            convergence_curve=convergence_curve,
            is_feasible=all_served and all_time_valid,
            constraint_status={
                "capacity_satisfied": all(r.total_load_kg <= problem.vehicle_capacity_kg for r in gbest_routes),
                "max_route_time_satisfied": all_time_valid,
                "all_customers_served": all_served,
                "soft_time_window_penalties": round(sum(r.time_window_penalties for r in gbest_routes), 2)
            },
            provenance={
                "road_network": "CURATED REAL GEOGRAPHY (Visakhapatnam Coordinates)",
                "traffic": "SIMULATED (BPR Engine)",
                "cost": "DERIVED",
                "optimization": "OPTIMIZATION RESULT (Random-Key QPSO)"
            }
        )
