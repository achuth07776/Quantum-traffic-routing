"""
Memetic Random-Key QPSO for Capacitated Vehicle Routing (VRP) with Time Windows.

Hybrid metaheuristic coupling the global exploration of Quantum-Behaved PSO
(Random-Key encoding, delta-potential-well position update) with a
permutation-level local search phase:
  - 2-opt: reverse any contiguous customer subsequence (intra/inter-route probe)
  - Relocate: move a single customer to any other insertion point
applied around the global best solution after every swarm iteration
(intensification) with feedback of the improved ordering re-encoded into the
swarm's gbest attractor (diversification signal). Every candidate is evaluated
through the identical validated capacity/time-window decoder, so constraint
handling is unchanged from the vanilla QPSO.
"""

import time
import random
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from optimization.vrp.vrp_models import VRPProblem, VRPResult
from optimization.vrp.vrp_baselines import VRPGraphHelper
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP


class MemeticRandomKeyQPSOVRP(RandomKeyQPSOVRP):
    def __init__(
        self,
        num_particles: int = 30,
        beta_max: float = 1.0,
        beta_min: float = 0.5,
        tw_penalty_weight: float = 5.0,
        ls_rounds: int = 2,
        improvement_mode: str = "best",
        reencode_gbest: bool = True,
        inject_particle: bool = True
    ):
        """
        ls_rounds: max local-search improvement rounds per swarm iteration.
        improvement_mode: "best" scans the full neighborhood and takes the best
                          improving move; "first" takes the first improvement (faster).
        reencode_gbest: re-encode improved ordering into gbest_position (attractor).
        inject_particle: also overwrite the current-best particle with the improved
                         gbest position (stronger convergence; may reduce diversity).
        """
        super().__init__(
            num_particles=num_particles,
            beta_max=beta_max,
            beta_min=beta_min,
            tw_penalty_weight=tw_penalty_weight
        )
        self.ls_rounds = max(1, int(ls_rounds))
        self.improvement_mode = improvement_mode if improvement_mode in ("best", "first") else "best"
        self.reencode_gbest = reencode_gbest
        self.inject_particle = inject_particle

    # ------------------------------------------------------------------
    # Encoding helpers: customer order <-> normalized random keys
    # ------------------------------------------------------------------
    def _order_to_particle(self, order: List[str], num_cust: int, customer_idx: Dict[str, int]) -> np.ndarray:
        keys = np.zeros(num_cust)
        n = len(order)
        if n <= 1:
            return keys
        for rank, node_id in enumerate(order):
            keys[customer_idx[node_id]] = -1.0 + 2.0 * rank / (n - 1)
        return keys

    def _evaluate_order(
        self,
        order: List[str],
        problem: VRPProblem,
        helper: Any,
        customer_idx: Dict[str, int]
    ) -> Tuple[List[Any], float, List[str]]:
        keys = self._order_to_particle(order, len(problem.customers), customer_idx)
        routes, cost, unserved = self._decode_and_repair(keys, problem, helper)
        return routes, cost, unserved

    def _neighborhood(self, order: List[str]):
        n = len(order)
        # 2-opt: reverse every contiguous subsequence of length >= 2
        for i in range(n):
            for j in range(i + 2, n):
                yield order[:i] + order[i:j + 1][::-1] + order[j + 1:]
        # Relocate: move each customer to every other insertion point
        for i in range(n):
            item = order[i]
            rest = order[:i] + order[i + 1:]
            for j in range(n):
                if j == i:
                    continue
                yield rest[:j] + [item] + rest[j:]

    def _local_search(
        self,
        order: List[str],
        problem: VRPProblem,
        helper: Any,
        customer_idx: Dict[str, int]
    ) -> Tuple[List[Any], float, List[str], List[str], int]:
        best_order: List[str] = list(order)
        best_routes, best_cost, best_unserved = self._evaluate_order(best_order, problem, helper, customer_idx)
        ls_evals = 1

        for _ in range(self.ls_rounds):
            improved = False
            for cand in self._neighborhood(best_order):
                ls_evals += 1
                cand_routes, cand_cost, cand_unserved = self._evaluate_order(cand, problem, helper, customer_idx)
                if cand_cost < best_cost - 1e-9:
                    best_order = cand
                    best_routes, best_cost, best_unserved = cand_routes, cand_cost, cand_unserved
                    improved = True
                    if self.improvement_mode == "first":
                        break
            if not improved:
                break

        return best_routes, best_cost, best_unserved, best_order, ls_evals

    # ------------------------------------------------------------------
    # Main memetic solve loop
    # ------------------------------------------------------------------
    def solve(self, graph: Optional[Any], problem: VRPProblem, helper: Optional[Any] = None) -> VRPResult:
        start_time = time.perf_counter()

        if problem.seed is not None:
            random.seed(problem.seed)
            np.random.seed(problem.seed)

        if helper is None:
            helper = VRPGraphHelper(graph, problem.weights)
        customer_idx = {c.node_id: i for i, c in enumerate(problem.customers)}
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
        gbest_routes = []
        gbest_unserved = []

        convergence_curve = []
        total_ls_evals = 0.0
        ls_improvements = 0

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

            # ---- Memetic phase: local search around gbest + feedback ----
            if gbest_routes:
                # Full permutation genome: served customers in decoded order,
                # then previously-unserved customers (so relocation can pull them
                # forward into service and reduce infeasibility penalties)
                served = [c for r in gbest_routes for c in r.customer_nodes]
                served_set = set(served)
                unserved_tail = [c.node_id for c in problem.customers if c.node_id not in served_set]
                order = served + unserved_tail
                if order:
                    ls_routes, ls_cost, ls_unserved, ls_order, ls_evals = self._local_search(
                        order, problem, helper, customer_idx
                    )
                    total_ls_evals += ls_evals
                    if ls_cost < gbest_cost - 1e-9:
                        gbest_routes = ls_routes
                        gbest_cost = ls_cost
                        gbest_unserved = ls_unserved
                        ls_improvements += 1
                        # Feedback: re-encode improved ordering so the swarm
                        # attracts toward the refined region in later iterations
                        if self.reencode_gbest:
                            gbest_position = self._order_to_particle(ls_order, num_cust, customer_idx)
                            if self.inject_particle:
                                particles[int(np.argmin(pbest_costs))] = np.copy(gbest_position)

            convergence_curve.append(round(gbest_cost if gbest_cost < float('inf') else 0.0, 3))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        total_fleet_time = sum(r.total_travel_time_min for r in gbest_routes)
        total_fleet_dist = sum(r.total_distance_km for r in gbest_routes)

        all_served = len(gbest_unserved) == 0
        all_time_valid = all(r.total_travel_time_min <= problem.max_route_time_min for r in gbest_routes)

        return VRPResult(
            algorithm_name="Memetic Random-Key QPSO (QPSO + 2-Opt/Relocate Local Search)",
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
                "soft_time_window_penalties": round(sum(r.time_window_penalties for r in gbest_routes), 2),
                "local_search_evaluations": int(total_ls_evals),
                "local_search_improvements": int(ls_improvements)
            },
            provenance={
                "road_network": "CURATED REAL GEOGRAPHY (Visakhapatnam Coordinates)",
                "traffic": "SIMULATED (BPR Engine)",
                "cost": "DERIVED",
                "optimization": "OPTIMIZATION RESULT (Memetic QPSO - QPSO + Local Search Hybrid)"
            }
        )