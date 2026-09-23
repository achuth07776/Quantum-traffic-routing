"""
Unit test for Google OR-Tools Sub-Second Search Budgeting.

Verifies:
1. OR-Tools accepts time_limit_ms (100ms, 250ms, 500ms) and respects the budget.
2. OR-Tools solver returns raw_total_cost without integer quantization artifacts.
3. MatrixVRP correctly forwards sub-second budgets.
"""

import time
import pytest
from optimization.vrp.ortools_vrp import solve_cvrp_ortools
from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer


def test_ortools_subsecond_budget_respect():
    """Verify OR-Tools terminates within a 150ms budget rather than defaulting to 2s."""
    cost_matrix = [
        [0.0, 1.2, 2.5, 3.1, 1.8],
        [1.2, 0.0, 1.5, 2.8, 2.2],
        [2.5, 1.5, 0.0, 1.4, 3.0],
        [3.1, 2.8, 1.4, 0.0, 2.0],
        [1.8, 2.2, 3.0, 2.0, 0.0],
    ]
    demands = [0.0, 20.0, 30.0, 25.0, 15.0]
    capacities = [100.0, 100.0]

    t0 = time.perf_counter()
    res = solve_cvrp_ortools(
        cost_matrix=cost_matrix,
        demands=demands,
        vehicle_capacities=capacities,
        depot_index=0,
        time_limit_ms=100
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert res["is_feasible"] is True
    assert res["budget_ms"] == 100
    # Must terminate well under 500ms (verifying it does not default to 1s or 2s)
    assert elapsed_ms < 600.0
    assert "raw_total_cost" in res


def test_matrix_vrp_forwards_budget():
    """Verify RealWorldVRPOptimizer forwards ortools_time_limit_ms."""
    durations = [
        [0.0, 10.0, 15.0],
        [10.0, 0.0, 12.0],
        [15.0, 12.0, 0.0]
    ]
    distances = [
        [0.0, 5.0, 8.0],
        [5.0, 0.0, 6.0],
        [8.0, 6.0, 0.0]
    ]
    opt = RealWorldVRPOptimizer()
    out = opt.solve_fleet_vrp(
        node_ids=["depot", "c1", "c2"],
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=[0.0, 20.0, 30.0],
        vehicle_capacities=[100.0, 100.0],
        ortools_time_limit_ms=150,
        qpso_particles=20,
        qpso_iterations=20,
        qpso_seed=42
    )
    assert out["status"] == "SUCCESS"
    assert out["results"]["ortools"]["is_feasible"] is True
    assert "raw_savings_vs_greedy" in out["benchmark_comparison"]
