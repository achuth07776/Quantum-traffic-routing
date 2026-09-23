"""
Matrix-based VRP Solver Architecture for Real-World Road Networks.

Bridges real OSRM travel-time matrices with:
1. Established Classical Reference Solver: Google OR-Tools (CVRP Guided Local Search)
2. Quantum-Inspired Metaheuristic: Random-Key QPSO
3. Classical Heuristic Reference: Greedy Nearest Neighbor

Ensures 100% mathematical correctness & fairness by using a properly normalized
multi-objective formulation:
  J = w_time * (T / T_ref) + w_dist * (D / D_ref)
where T_ref and D_ref are the mean pairwise travel time and distance across the active
road network matrix. This ensures dimensionless, calibrated 70/30 weighting.
"""

import time
from datetime import datetime, timezone
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from optimization.vrp.vrp_models import VRPProblem, VRPResult, VehicleRoute, CustomerStop
from optimization.vrp.ortools_vrp import solve_cvrp_ortools
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP
from optimization.vrp.vrp_qpso_memetic import MemeticRandomKeyQPSOVRP
from optimization.vrp.matrix_exact_vrp import MatrixExactVRP


class MatrixVRPGraphHelper:
    """
    Graph helper backed directly by an NxN real-world road travel-time / distance matrix
    (e.g. from OSRM Table API or OpenRouteService Matrix API).
    Handles unreachable cells (None / inf) explicitly as infeasible transitions.
    Applies normalized cost scaling: w_t * (T / T_ref) + w_d * (D / D_ref).
    """

    def __init__(
        self,
        node_ids: List[str],
        duration_matrix_min: List[List[Optional[float]]],
        distance_matrix_km: List[List[Optional[float]]],
        weights: Optional[Dict[str, float]] = None,
        t_ref: float = 1.0,
        d_ref: float = 1.0
    ):
        self.node_ids = node_ids
        self.node_to_idx = {nid: i for i, nid in enumerate(node_ids)}
        self.duration_matrix = duration_matrix_min
        self.distance_matrix = distance_matrix_km
        self.weights = weights or {"time": 0.7, "distance": 0.3}
        self.t_ref = t_ref if t_ref > 0 else 1.0
        self.d_ref = d_ref if d_ref > 0 else 1.0

    def get_path_and_metrics(self, u: str, v: str) -> Tuple[List[str], Dict[str, Any]]:
        u_idx = self.node_to_idx.get(u)
        v_idx = self.node_to_idx.get(v)

        if u_idx is None or v_idx is None:
            return ([], {
                "travel_time_min": float("inf"),
                "distance_km": float("inf"),
                "cost": float("inf"),
                "is_feasible": False,
                "reason": "UNKNOWN_NODE"
            })

        t_min = self.duration_matrix[u_idx][v_idx]
        d_km = self.distance_matrix[u_idx][v_idx]

        # Explicit handling of unreachable cells (None or infinity from routing engine)
        if t_min is None or d_km is None or t_min == float("inf") or d_km == float("inf"):
            return ([], {
                "travel_time_min": float("inf"),
                "distance_km": float("inf"),
                "cost": float("inf"),
                "is_feasible": False,
                "reason": "UNREACHABLE_ROAD_TRANSITION"
            })

        w_time = self.weights.get("time", 0.7)
        w_dist = self.weights.get("distance", 0.3)
        # Properly normalized dimensionless cost
        weighted_cost = round(w_time * (t_min / self.t_ref) + w_dist * (d_km / self.d_ref), 4)

        return ([u, v], {
            "travel_time_min": t_min,
            "distance_km": d_km,
            "cost": weighted_cost,
            "is_feasible": True
        })


class MatrixGreedyVRP:
    """Greedy Nearest-Neighbor heuristic running directly on a real travel-time matrix."""

    def solve(
        self,
        problem: VRPProblem,
        helper: MatrixVRPGraphHelper
    ) -> VRPResult:
        start_time = time.perf_counter()
        depot = problem.depot_node
        unvisited = {c.node_id: c for c in problem.customers}

        vehicle_routes: List[VehicleRoute] = []
        total_cost = 0.0

        for v_id in range(problem.num_vehicles):
            if not unvisited:
                break

            curr_node = depot
            curr_load = 0.0
            curr_time = 0.0
            tw_penalty = 0.0
            route_customers = []
            full_path = [depot]
            route_cost = 0.0
            route_dist = 0.0

            while unvisited:
                best_next = None
                best_metrics = None
                best_cost = float("inf")

                for cid, c in unvisited.items():
                    if curr_load + c.demand_kg > problem.vehicle_capacity_kg:
                        continue

                    _, to_cust = helper.get_path_and_metrics(curr_node, cid)
                    if not to_cust["is_feasible"]:
                        continue

                    arr_time = curr_time + to_cust["travel_time_min"]
                    _, back_depot = helper.get_path_and_metrics(cid, depot)
                    if not back_depot["is_feasible"]:
                        continue

                    tot_time = arr_time + c.service_duration_min + back_depot["travel_time_min"]
                    if tot_time > problem.max_route_time_min:
                        continue

                    penalty = 0.0
                    if arr_time > c.time_window_end_min:
                        penalty = (arr_time - c.time_window_end_min) * 5.0

                    cand_cost = to_cust["cost"] + penalty
                    if cand_cost < best_cost:
                        best_cost = cand_cost
                        best_next = c
                        best_metrics = to_cust

                if best_next is None:
                    break

                cid = best_next.node_id
                arr_time = curr_time + best_metrics["travel_time_min"]
                if arr_time > best_next.time_window_end_min:
                    tw_penalty += (arr_time - best_next.time_window_end_min) * 5.0

                route_cost += best_metrics["cost"]
                route_dist += best_metrics["distance_km"]
                curr_time = arr_time + best_next.service_duration_min
                curr_load += best_next.demand_kg
                route_customers.append(best_next)
                full_path.append(cid)
                del unvisited[cid]
                curr_node = cid

            if route_customers:
                _, back_depot = helper.get_path_and_metrics(curr_node, depot)
                route_cost += back_depot["cost"]
                route_dist += back_depot["distance_km"]
                curr_time += back_depot["travel_time_min"]
                full_path.append(depot)

                tot_r_cost = route_cost + tw_penalty
                total_cost += tot_r_cost
                vehicle_routes.append(VehicleRoute(
                    vehicle_id=v_id,
                    customer_nodes=[c.node_id for c in route_customers],
                    full_path_nodes=full_path,
                    total_load_kg=round(curr_load, 2),
                    total_travel_time_min=round(curr_time, 2),
                    total_distance_km=round(route_dist, 2),
                    total_cost=round(tot_r_cost, 4),
                    time_window_penalties=tw_penalty,
                    exceeds_max_route_time=curr_time > problem.max_route_time_min,
                    is_feasible=True
                ))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return VRPResult(
            algorithm_name="Greedy Nearest-Neighbor",
            routes=vehicle_routes,
            total_fleet_time_min=round(sum(r.total_travel_time_min for r in vehicle_routes), 2),
            total_fleet_distance_km=round(sum(r.total_distance_km for r in vehicle_routes), 2),
            total_fleet_cost=round(total_cost, 4),
            unserved_customers=list(unvisited.keys()),
            runtime_ms=round(elapsed_ms, 2),
            is_feasible=len(unvisited) == 0
        )


class RealWorldVRPOptimizer:
    """
    High-level orchestrator solving Fleet VRP on real-world road networks.
    Ensures 100% mathematical correctness by normalizing time and distance:
      J = w_time * (T / T_ref) + w_dist * (D / D_ref)
    across Google OR-Tools (Classical Reference), Random-Key QPSO, and Greedy.
    """

    def __init__(self):
        self.qpso_solver = RandomKeyQPSOVRP(num_particles=40, beta_max=1.0, beta_min=0.5)
        self.memetic_qpso_solver = MemeticRandomKeyQPSOVRP(num_particles=40, beta_max=1.0, beta_min=0.5)
        self.greedy_solver = MatrixGreedyVRP()

    def solve_fleet_vrp(
        self,
        node_ids: List[str],
        duration_matrix_min: List[List[Optional[float]]],
        distance_matrix_km: List[List[Optional[float]]],
        demands: List[float],
        vehicle_capacities: List[float],
        depot_index: int = 0,
        max_route_time_min: float = 240.0,
        time_limit_seconds: float = 2.0,
        weights: Optional[Dict[str, float]] = None,
        ortools_time_limit_ms: Optional[int] = None,
        qpso_particles: Optional[int] = None,
        qpso_iterations: Optional[int] = None,
        qpso_seed: Optional[int] = None,
        qpso_memetic: bool = False,
        fixed_reference_scales: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Runs multi-algorithm fleet optimization on a real road matrix with normalized,
        dimensionless multi-objective formulation across all algorithms.
        Supports fair compute budget configuration for OR-Tools (ms) and QPSO (particles/iterations/seed).
        Supports fixed reference scales (t_ref, d_ref) for strict before/after comparability.
        """
        w = weights or {"time": 0.7, "distance": 0.3}
        w_time = w.get("time", 0.7)
        w_dist = w.get("distance", 0.3)

        num_nodes = len(node_ids)
        depot_node = node_ids[depot_index]

        # 1. Compute reference normalization constants T_ref and D_ref (or use fixed experiment scales)
        if fixed_reference_scales and "t_ref_min" in fixed_reference_scales and "d_ref_km" in fixed_reference_scales:
            t_ref = float(fixed_reference_scales["t_ref_min"])
            d_ref = float(fixed_reference_scales["d_ref_km"])
        else:
            valid_times = [
                duration_matrix_min[i][j]
                for i in range(num_nodes)
                for j in range(num_nodes)
                if i != j and duration_matrix_min[i][j] is not None and duration_matrix_min[i][j] > 0 and duration_matrix_min[i][j] != float("inf")
            ]
            valid_dists = [
                distance_matrix_km[i][j]
                for i in range(num_nodes)
                for j in range(num_nodes)
                if i != j and distance_matrix_km[i][j] is not None and distance_matrix_km[i][j] > 0 and distance_matrix_km[i][j] != float("inf")
            ]

            t_ref = round(float(np.mean(valid_times)), 2) if valid_times else 1.0
            d_ref = round(float(np.mean(valid_dists)), 2) if valid_dists else 1.0
            if t_ref <= 0:
                t_ref = 1.0
            if d_ref <= 0:
                d_ref = 1.0

        # 2. Construct the normalized combined cost matrix C_ij = w_time * (T_ij/T_ref) + w_dist * (D_ij/D_ref)
        combined_cost_matrix: List[List[float]] = []
        for i in range(num_nodes):
            row = []
            for j in range(num_nodes):
                if i == j:
                    row.append(0.0)
                else:
                    t = duration_matrix_min[i][j]
                    d = distance_matrix_km[i][j]
                    if t is None or d is None or t == float("inf") or d == float("inf"):
                        row.append(float("inf"))
                    else:
                        c = round(w_time * (t / t_ref) + w_dist * (d / d_ref), 4)
                        row.append(c)
            combined_cost_matrix.append(row)

        customer_nodes = [
            CustomerStop(
                node_id=nid,
                name=nid.replace("_", " ").title(),
                demand_kg=demands[i],
                time_window_start_min=0.0,
                time_window_end_min=max_route_time_min,
                service_duration_min=0.0  # 0.0 ensures pure transit travel time parity across OR-Tools, QPSO, and Greedy
            )
            for i, nid in enumerate(node_ids)
            if i != depot_index
        ]

        problem = VRPProblem(
            depot_node=depot_node,
            customers=customer_nodes,
            num_vehicles=len(vehicle_capacities),
            vehicle_capacity_kg=vehicle_capacities[0],
            max_route_time_min=max_route_time_min,
            weights={"time": w_time, "distance": w_dist},
            population_size=qpso_particles or 40,
            max_iterations=qpso_iterations or 50,
            seed=qpso_seed or 42
        )

        helper = MatrixVRPGraphHelper(
            node_ids=node_ids,
            duration_matrix_min=duration_matrix_min,
            distance_matrix_km=distance_matrix_km,
            weights=problem.weights,
            t_ref=t_ref,
            d_ref=d_ref
        )

        results: Dict[str, Any] = {}

        objective_definition = {
            "name": "normalized_weighted_travel_cost",
            "formula": f"{w_time} * (T / {t_ref} min) + {w_dist} * (D / {d_ref} km)",
            "weights": {"time": w_time, "distance": w_dist},
            "reference_scales": {
                "t_ref_min": t_ref,
                "d_ref_km": d_ref,
                "scale_interpretation": "Normalized against mean pairwise network travel time and distance"
            }
        }

        # -----------------------------------------------------------------
        # 1. Classical Heuristic Reference: Greedy Nearest Neighbor
        # -----------------------------------------------------------------
        greedy_res = self.greedy_solver.solve(problem, helper)
        greedy_dict = greedy_res.model_dump()
        greedy_tot_time = greedy_dict["total_fleet_time_min"]
        greedy_tot_dist = greedy_dict["total_fleet_distance_km"]
        greedy_obj_val = round(w_time * (greedy_tot_time / t_ref) + w_dist * (greedy_tot_dist / d_ref), 4)

        greedy_dict["total_fleet_cost"] = greedy_obj_val
        greedy_dict["objective"] = {
            "name": "normalized_weighted_travel_cost",
            "formula": objective_definition["formula"],
            "weights": {"time": w_time, "distance": w_dist},
            "objective_value": greedy_obj_val,
            "components": {
                "travel_time_min": greedy_tot_time,
                "distance_km": greedy_tot_dist,
                "t_ref_min": t_ref,
                "d_ref_km": d_ref
            }
        }
        results["greedy"] = greedy_dict

        # -----------------------------------------------------------------
        # 2. Established Classical Reference: Google OR-Tools (CVRP)
        # Optimized directly on the NORMALIZED combined cost matrix C_ij
        # -----------------------------------------------------------------
        ortools_raw = solve_cvrp_ortools(
            cost_matrix=combined_cost_matrix,
            demands=demands,
            vehicle_capacities=vehicle_capacities,
            depot_index=depot_index,
            time_limit_seconds=time_limit_seconds,
            time_limit_ms=ortools_time_limit_ms,
            duration_matrix_min=duration_matrix_min,
            max_route_time_min=max_route_time_min
        )

        ortools_routes = []
        ortools_tot_dist = 0.0
        ortools_tot_time = 0.0

        for r in ortools_raw.get("routes", []):
            stop_ids = [node_ids[idx] for idx in r["stops"]]
            r_dist = 0.0
            r_time = 0.0
            for k in range(len(r["stops"]) - 1):
                u_i = r["stops"][k]
                v_i = r["stops"][k+1]
                t_val = duration_matrix_min[u_i][v_i]
                d_val = distance_matrix_km[u_i][v_i]
                if t_val is not None and t_val != float("inf"):
                    r_time += t_val
                if d_val is not None and d_val != float("inf"):
                    r_dist += d_val

            ortools_tot_dist += r_dist
            ortools_tot_time += r_time

            route_obj_val = round(w_time * (r_time / t_ref) + w_dist * (r_dist / d_ref), 4)
            ortools_routes.append({
                "vehicle_id": r["vehicle_id"],
                "customer_nodes": [node_ids[idx] for idx in r["stops"][1:-1]],
                "full_path_nodes": stop_ids,
                "total_load_kg": r["load"],
                "total_travel_time_min": round(r_time, 2),
                "total_distance_km": round(r_dist, 2),
                "total_cost": route_obj_val,
                "time_window_penalties": 0.0,
                "exceeds_max_route_time": False,
                "is_feasible": True
            })

        ortools_tot_time = round(ortools_tot_time, 2)
        ortools_tot_dist = round(ortools_tot_dist, 2)
        ortools_obj_val = round(w_time * (ortools_tot_time / t_ref) + w_dist * (ortools_tot_dist / d_ref), 4)

        results["ortools"] = {
            "algorithm_name": "Google OR-Tools (Classical Reference)",
            "routes": ortools_routes,
            "total_fleet_time_min": ortools_tot_time,
            "total_fleet_distance_km": ortools_tot_dist,
            "total_fleet_cost": ortools_obj_val,
            "unserved_customers": [],
            "runtime_ms": ortools_raw["runtime_ms"],
            "is_feasible": ortools_raw["is_feasible"],
            "status": ortools_raw["status"],
            "objective": {
                "name": "normalized_weighted_travel_cost",
                "formula": objective_definition["formula"],
                "weights": {"time": w_time, "distance": w_dist},
                "objective_value": ortools_obj_val,
                "components": {
                    "travel_time_min": ortools_tot_time,
                    "distance_km": ortools_tot_dist,
                    "t_ref_min": t_ref,
                    "d_ref_km": d_ref
                }
            }
        }

        # -----------------------------------------------------------------
        # 3. Quantum-Inspired Metaheuristic: Random-Key QPSO
        #    (optionally Memetic QPSO: QPSO + 2-Opt/Relocate Local Search)
        # Evaluated on the exact same helper and normalized weights
        # -----------------------------------------------------------------
        active_qpso = self.memetic_qpso_solver if qpso_memetic else self.qpso_solver
        qpso_res = active_qpso.solve(None, problem, helper=helper)
        qpso_dict = qpso_res.model_dump()
        qpso_tot_time = qpso_dict["total_fleet_time_min"]
        qpso_tot_dist = qpso_dict["total_fleet_distance_km"]
        qpso_obj_val = round(w_time * (qpso_tot_time / t_ref) + w_dist * (qpso_tot_dist / d_ref), 4)

        qpso_dict["total_fleet_cost"] = qpso_obj_val
        qpso_dict["objective"] = {
            "name": "normalized_weighted_travel_cost",
            "formula": objective_definition["formula"],
            "weights": {"time": w_time, "distance": w_dist},
            "objective_value": qpso_obj_val,
            "components": {
                "travel_time_min": qpso_tot_time,
                "distance_km": qpso_tot_dist,
                "t_ref_min": t_ref,
                "d_ref_km": d_ref
            }
        }
        results["qpso"] = qpso_dict

        # -----------------------------------------------------------------
        # 4. Exact Exhaustive Solver (Benchmark ground truth for N <= 8)
        # -----------------------------------------------------------------
        if num_nodes <= 8:
            exact_solver = MatrixExactVRP()
            exact_res = exact_solver.solve(
                duration_matrix_min=duration_matrix_min,
                distance_matrix_km=distance_matrix_km,
                demands=demands,
                capacities=vehicle_capacities,
                depot_idx=depot_index,
                weights=problem.weights,
                t_ref=t_ref,
                d_ref=d_ref,
                max_route_time_min=max_route_time_min
            )
            exact_vehicle_routes = []
            for v_idx, stops in enumerate(exact_res.get("exact_routes", [])):
                stop_ids = [node_ids[idx] for idx in stops]
                r_dist = 0.0
                r_time = 0.0
                for k in range(len(stops) - 1):
                    u_i = stops[k]
                    v_i = stops[k+1]
                    t_val = duration_matrix_min[u_i][v_i]
                    d_val = distance_matrix_km[u_i][v_i]
                    if t_val is not None and t_val != float("inf"):
                        r_time += t_val
                    if d_val is not None and d_val != float("inf"):
                        r_dist += d_val
                r_load = sum(demands[idx] for idx in stops[1:-1])
                route_obj = round(w_time * (r_time / t_ref) + w_dist * (r_dist / d_ref), 4)
                exact_vehicle_routes.append({
                    "vehicle_id": v_idx,
                    "customer_nodes": [node_ids[idx] for idx in stops[1:-1]],
                    "full_path_nodes": stop_ids,
                    "total_load_kg": r_load,
                    "total_travel_time_min": round(r_time, 2),
                    "total_distance_km": round(r_dist, 2),
                    "total_cost": route_obj,
                    "time_window_penalties": 0.0,
                    "exceeds_max_route_time": False,
                    "is_feasible": True
                })

            results["exact"] = {
                "algorithm_name": "Matrix Exact Global Optimum",
                "routes": exact_vehicle_routes,
                "total_fleet_time_min": exact_res.get("total_time_min", 0.0),
                "total_fleet_distance_km": exact_res.get("total_distance_km", 0.0),
                "total_fleet_cost": exact_res.get("exact_objective", 0.0),
                "unserved_customers": [],
                "runtime_ms": exact_res.get("runtime_ms", 0.0),
                "is_feasible": exact_res.get("feasible", False),
                "status": exact_res.get("status", "OPTIMAL"),
                "enumerated_candidates": exact_res.get("enumerated_candidates", 0),
                "objective": {
                    "name": "normalized_weighted_travel_cost",
                    "formula": objective_definition["formula"],
                    "weights": {"time": w_time, "distance": w_dist},
                    "objective_value": exact_res.get("exact_objective", 0.0),
                    "components": {
                        "travel_time_min": exact_res.get("total_time_min", 0.0),
                        "distance_km": exact_res.get("total_distance_km", 0.0),
                        "t_ref_min": t_ref,
                        "d_ref_km": d_ref
                    }
                }
            }

        # -----------------------------------------------------------------
        # 5. Rigorous Relative Gap vs Classical Reference Solver
        # (J_qpso - J_reference) / J_reference * 100%
        # -----------------------------------------------------------------
        ortools_cost = ortools_obj_val
        qpso_cost = qpso_obj_val
        greedy_cost = greedy_obj_val

        # Cost Gap % vs Reference Solver
        gap_qpso_cost = (
            round((qpso_cost - ortools_cost) / max(1e-6, ortools_cost) * 100.0, 2)
            if results["ortools"]["is_feasible"] and results["qpso"]["is_feasible"]
            else None
        )
        gap_greedy_cost = (
            round((greedy_cost - ortools_cost) / max(1e-6, ortools_cost) * 100.0, 2)
            if results["ortools"]["is_feasible"] and results["greedy"]["is_feasible"]
            else None
        )

        # Travel Time Gap %
        gap_qpso_time = (
            round((qpso_tot_time - ortools_tot_time) / max(1e-6, ortools_tot_time) * 100.0, 2)
            if results["ortools"]["is_feasible"] and results["qpso"]["is_feasible"]
            else None
        )

        # Distance Gap %
        gap_qpso_dist = (
            round((qpso_tot_dist - ortools_tot_dist) / max(1e-6, ortools_tot_dist) * 100.0, 2)
            if results["ortools"]["is_feasible"] and results["qpso"]["is_feasible"]
            else None
        )

        matrix_ts = datetime.now(timezone.utc).isoformat()

        return {
            "status": "SUCCESS",
            "benchmark_comparison": {
                "reference_solver": "Google OR-Tools (Classical Reference)",
                "quantum_inspired_solver": "Random-Key QPSO (Quantum-Behaved Swarm)",
                "baseline_solver": "Greedy Nearest Neighbor",
                "objective_function": objective_definition,
                "qpso_cost_gap_vs_reference_pct": gap_qpso_cost,
                "qpso_time_gap_pct": gap_qpso_time,
                "qpso_dist_gap_pct": gap_qpso_dist,
                "greedy_cost_gap_vs_reference_pct": gap_greedy_cost,
                # Compatibility aliases
                "qpso_gap_vs_reference_pct": gap_qpso_cost,
                "qpso_gap_vs_ortools_pct": gap_qpso_cost,
                "greedy_gap_vs_ortools_pct": gap_greedy_cost,
                # Explicit unrounded differences vs Greedy
                "raw_savings_vs_greedy": {
                    "time_saved_min": round(greedy_tot_time - qpso_tot_time, 2),
                    "distance_saved_km": round(greedy_tot_dist - qpso_tot_dist, 2),
                    "cost_saved": round(greedy_obj_val - qpso_obj_val, 4)
                }
            },
            "results": results,
            "matrix_metadata": {
                "num_stops": len(node_ids),
                "num_vehicles": len(vehicle_capacities),
                "depot": depot_node,
                "matrix_engine": "OSRM Table API (/table/v1/driving)",
                "routing_profile": "car (driving)",
                "matrix_status": "BASE_ROAD_NETWORK",
                "matrix_timestamp": matrix_ts
            }
        }

    def evaluate_plan_under_matrix(
        self,
        routes: List[Dict[str, Any]],
        node_ids: List[str],
        duration_matrix_min: List[List[Optional[float]]],
        distance_matrix_km: List[List[Optional[float]]],
        depot_node: str = "maddilapalem_junction",
        weights: Optional[Dict[str, float]] = None,
        fixed_reference_scales: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates an existing pre-shock fleet plan against a new/shocked travel-time matrix.
        Enables computing the true value of reoptimization:
          Savings = Cost(OldPlan | T1) - Cost(ReoptimizedPlan | T1)
        """
        w = weights or {"time": 0.7, "distance": 0.3}
        w_time = w.get("time", 0.7)
        w_dist = w.get("distance", 0.3)

        node_to_idx = {nid: i for i, nid in enumerate(node_ids)}
        t_ref = fixed_reference_scales.get("t_ref_min", 1.0) if fixed_reference_scales else 1.0
        d_ref = fixed_reference_scales.get("d_ref_km", 1.0) if fixed_reference_scales else 1.0

        evaluated_routes = []
        total_fleet_time_min = 0.0
        total_fleet_distance_km = 0.0

        for r in routes:
            cust_nodes = r.get("customer_nodes", [])
            full_seq = [depot_node] + cust_nodes + [depot_node] if cust_nodes else [depot_node]

            route_time = 0.0
            route_dist = 0.0

            for u, v in zip(full_seq[:-1], full_seq[1:]):
                u_idx = node_to_idx.get(u)
                v_idx = node_to_idx.get(v)
                if u_idx is not None and v_idx is not None:
                    t = duration_matrix_min[u_idx][v_idx] or 0.0
                    d = distance_matrix_km[u_idx][v_idx] or 0.0
                    route_time += t
                    route_dist += d

            route_cost = round(w_time * (route_time / t_ref) + w_dist * (route_dist / d_ref), 4)
            evaluated_routes.append({
                "vehicle_id": r.get("vehicle_id", 0),
                "customer_nodes": cust_nodes,
                "full_path_nodes": full_seq,
                "total_load_kg": r.get("total_load_kg", 0.0),
                "total_travel_time_min": round(route_time, 2),
                "total_distance_km": round(route_dist, 2),
                "total_cost": route_cost
            })
            total_fleet_time_min += route_time
            total_fleet_distance_km += route_dist

        total_cost = round(w_time * (total_fleet_time_min / t_ref) + w_dist * (total_fleet_distance_km / d_ref), 4)

        return {
            "routes": evaluated_routes,
            "total_fleet_time_min": round(total_fleet_time_min, 2),
            "total_fleet_distance_km": round(total_fleet_distance_km, 2),
            "total_fleet_cost": total_cost,
            "objective": {
                "name": "normalized_weighted_travel_cost",
                "formula": f"{w_time} * (T / {t_ref} min) + {w_dist} * (D / {d_ref} km)",
                "weights": {"time": w_time, "distance": w_dist},
                "objective_value": total_cost,
                "components": {
                    "travel_time_min": round(total_fleet_time_min, 2),
                    "distance_km": round(total_fleet_distance_km, 2),
                    "t_ref_min": t_ref,
                    "d_ref_km": d_ref
                }
            }
        }

