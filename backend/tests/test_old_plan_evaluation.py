"""
Unit Test: Pre-Shock Plan Evaluation & Delay Avoidance Hero Metric.

Verifies:
1. evaluate_plan_under_matrix computes exact travel time and distance for an existing route on a new matrix.
2. In a traffic shock, Time(OldPlan | T1) > Time(Reoptimized | T1).
3. Savings = Time(OldPlan | T1) - Time(Reoptimized | T1) > 0.
"""

import pytest
from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer


def test_old_plan_evaluation_and_savings():
    optimizer = RealWorldVRPOptimizer()
    node_ids = ["depot", "a", "b"]
    depot = "depot"
    fixed_scales = {"t_ref_min": 15.0, "d_ref_km": 15.0}

    # Baseline Matrix T0:
    # depot -> a (10m), a -> b (10m), b -> depot (10m). Total = 30m
    # depot -> b (12m), b -> a (12m), a -> depot (12m). Total = 36m
    # Optimal T0 route: depot -> a -> b -> depot (30m)
    t0_durations = [
        [0.0, 10.0, 12.0],
        [10.0, 0.0, 10.0],
        [12.0, 10.0, 0.0]
    ]
    distances = [
        [0.0, 10.0, 12.0],
        [10.0, 0.0, 10.0],
        [12.0, 10.0, 0.0]
    ]

    routes_t0 = [{
        "vehicle_id": 0,
        "customer_nodes": ["a", "b"],
        "total_load_kg": 100.0
    }]

    # Traffic Shock on corridor (a <-> b): duration jumps from 10m to 40m!
    t1_durations = [
        [0.0, 10.0, 12.0],
        [10.0, 0.0, 40.0],  # Shocked
        [12.0, 40.0, 0.0]
    ]

    # Evaluate old plan on T1:
    # depot -> a (10m) + a -> b (40m) + b -> depot (12m) = 62m!
    old_plan_eval = optimizer.evaluate_plan_under_matrix(
        routes=routes_t0,
        node_ids=node_ids,
        duration_matrix_min=t1_durations,
        distance_matrix_km=distances,
        depot_node=depot,
        fixed_reference_scales=fixed_scales
    )
    assert old_plan_eval["total_fleet_time_min"] == 62.0

    # Solve T1 reoptimization:
    # An alternative route might be vehicle 1 serves 'a' and returns, vehicle 2 serves 'b' and returns:
    # depot -> a -> depot (20m) + depot -> b -> depot (24m) = 44m!
    plan_t1 = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=t1_durations,
        distance_matrix_km=distances,
        demands=[0.0, 50.0, 50.0],
        vehicle_capacities=[300.0, 300.0],
        depot_index=0,
        fixed_reference_scales=fixed_scales
    )
    reopt_time = plan_t1["results"]["ortools"]["total_fleet_time_min"]

    # Reoptimized time must be strictly better than staying on the shocked old plan!
    assert reopt_time < old_plan_eval["total_fleet_time_min"]
    savings = old_plan_eval["total_fleet_time_min"] - reopt_time
    assert savings > 0.0
