"""
Matrix Exact Exhaustive VRP Solver.

Operates directly on the common NxN duration and distance matrices for N <= 8.
Guarantees finding the mathematically exact global minimum of the normalized objective:
    J = w_time * (T / T_ref) + w_distance * (D / D_ref)
subject to vehicle capacity and optional route duration constraints.
"""

import time
import math
import itertools
from typing import List, Dict, Any, Optional


class MatrixExactVRP:
    """
    Exact Exhaustive Permutation and Partition Solver for small matrix VRP instances (N <= 8).
    Shares the exact same matrix, cost function, and constraints as OR-Tools and QPSO.
    """

    def solve(
        self,
        duration_matrix_min: List[List[float]],
        distance_matrix_km: List[List[float]],
        demands: List[float],
        capacities: List[float],
        depot_idx: int = 0,
        weights: Optional[Dict[str, float]] = None,
        t_ref: Optional[float] = None,
        d_ref: Optional[float] = None,
        max_route_time_min: Optional[float] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        n = len(duration_matrix_min)
        num_vehicles = len(capacities)
        customer_indices = [i for i in range(n) if i != depot_idx]
        num_customers = len(customer_indices)

        if num_customers > 8:
            raise ValueError(
                f"MatrixExactVRP is bounded to N <= 8 locations (received {n} total locations)."
            )

        w = weights or {"time": 0.7, "distance": 0.3}
        w_time = float(w.get("time", 0.7))
        w_dist = float(w.get("distance", 0.3))

        # Default normalizers if not provided
        ref_time = t_ref if t_ref and t_ref > 0 else 60.0
        ref_dist = d_ref if d_ref and d_ref > 0 else 20.0

        best_objective = float("inf")
        best_routes: List[List[int]] = []
        best_total_time = float("inf")
        best_total_dist = float("inf")
        enumerated_count = 0
        found_feasible = False

        if num_customers == 0:
            return {
                "status": "OPTIMAL",
                "algorithm": "Matrix Exact Exhaustive Solver",
                "exact_objective": 0.0,
                "raw_exact_objective": 0.0,
                "exact_routes": [],
                "total_time_min": 0.0,
                "total_distance_km": 0.0,
                "feasible": True,
                "enumerated_candidates": 0,
                "runtime_ms": 0.0
            }

        # Enumerate all permutations of customer sequences
        for perm in itertools.permutations(customer_indices):
            # Enumerate all partitions of the customer sequence among num_vehicles
            for dividers in itertools.combinations(
                range(num_customers + num_vehicles - 1), num_vehicles - 1
            ):
                enumerated_count += 1
                vehicle_subsets: List[List[int]] = []
                last_div = -1
                item_idx = 0

                for div in list(dividers) + [num_customers + num_vehicles - 1]:
                    num_items = div - last_div - 1
                    vehicle_subsets.append(list(perm[item_idx : item_idx + num_items]))
                    item_idx += num_items
                    last_div = div

                # Evaluate feasibility & cost of this partition
                partition_valid = True
                partition_time = 0.0
                partition_dist = 0.0
                active_routes: List[List[int]] = []

                for v_id, subset in enumerate(vehicle_subsets):
                    if not subset:
                        continue

                    # Check vehicle capacity
                    route_demand = sum(demands[c] for c in subset)
                    if route_demand > capacities[v_id]:
                        partition_valid = False
                        break

                    # Trace route: depot -> stop1 -> stop2 -> ... -> depot
                    route_time = 0.0
                    route_dist = 0.0
                    curr = depot_idx

                    for nxt in subset:
                        dt = duration_matrix_min[curr][nxt]
                        dd = distance_matrix_km[curr][nxt]
                        if dt is None or dd is None or dt == float("inf") or dd == float("inf") or (isinstance(dt, float) and math.isinf(dt)) or (isinstance(dd, float) and math.isinf(dd)):
                            partition_valid = False
                            break
                        route_time += dt
                        route_dist += dd
                        curr = nxt

                    if not partition_valid:
                        break

                    # Return to depot
                    ret_t = duration_matrix_min[curr][depot_idx]
                    ret_d = distance_matrix_km[curr][depot_idx]
                    if ret_t is None or ret_d is None or ret_t == float("inf") or ret_d == float("inf") or (isinstance(ret_t, float) and math.isinf(ret_t)) or (isinstance(ret_d, float) and math.isinf(ret_d)):
                        partition_valid = False
                        break
                    route_time += ret_t
                    route_dist += ret_d

                    if max_route_time_min is not None and route_time > max_route_time_min:
                        partition_valid = False
                        break

                    partition_time += route_time
                    partition_dist += route_dist
                    active_routes.append([depot_idx] + subset + [depot_idx])

                if not partition_valid:
                    continue

                found_feasible = True
                # Normalized objective: J = w_time * (T / T_ref) + w_distance * (D / D_ref)
                obj_val = w_time * (partition_time / ref_time) + w_dist * (partition_dist / ref_dist)

                if obj_val < best_objective:
                    best_objective = obj_val
                    best_routes = active_routes
                    best_total_time = partition_time
                    best_total_dist = partition_dist

        runtime_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        if not found_feasible:
            return {
                "status": "INFEASIBLE",
                "algorithm": "Matrix Exact Exhaustive Solver",
                "exact_objective": float("inf"),
                "raw_exact_objective": float("inf"),
                "exact_routes": [],
                "total_time_min": float("inf"),
                "total_distance_km": float("inf"),
                "feasible": False,
                "enumerated_candidates": enumerated_count,
                "runtime_ms": runtime_ms
            }

        return {
            "status": "OPTIMAL",
            "algorithm": "Matrix Exact Exhaustive Solver",
            "exact_objective": round(best_objective, 4),
            "raw_exact_objective": best_objective,
            "exact_routes": best_routes,
            "total_time_min": round(best_total_time, 2),
            "total_distance_km": round(best_total_dist, 2),
            "feasible": True,
            "enumerated_candidates": enumerated_count,
            "runtime_ms": runtime_ms
        }
