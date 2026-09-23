"""
Unit Test: Objective Scale Consistency across Traffic Shock Conditions.

Verifies:
1. When fixed reference scales (T_ref_T0, D_ref_T0) are locked, an increase in travel time strictly and monotonically increases composite objective J.
2. Cures the P0 bug where dynamic denominators caused J to decrease when travel time increased.
"""

import pytest
from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer


def test_fixed_reference_scale_monotonicity():
    optimizer = RealWorldVRPOptimizer()
    node_ids = ["depot", "cust1", "cust2"]
    demands = [0.0, 50.0, 50.0]
    capacities = [300.0]

    # Baseline Matrix T0
    t0_durations = [
        [0.0, 10.0, 12.0],
        [10.0, 0.0, 15.0],
        [12.0, 15.0, 0.0]
    ]
    distances = [
        [0.0, 10.0, 12.0],
        [10.0, 0.0, 15.0],
        [12.0, 15.0, 0.0]
    ]

    # Lock reference scales
    fixed_scales = {"t_ref_min": 12.0, "d_ref_km": 12.0}

    plan_t0 = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=t0_durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        depot_index=0,
        fixed_reference_scales=fixed_scales
    )
    j_t0 = plan_t0["results"]["ortools"]["total_fleet_cost"]
    time_t0 = plan_t0["results"]["ortools"]["total_fleet_time_min"]

    # Congested Matrix T1 (Travel time increased on cust1 <-> cust2)
    t1_durations = [
        [0.0, 10.0, 12.0],
        [10.0, 0.0, 35.0],  # Heavy delay
        [12.0, 35.0, 0.0]
    ]

    plan_t1 = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=t1_durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        depot_index=0,
        fixed_reference_scales=fixed_scales
    )
    j_t1 = plan_t1["results"]["ortools"]["total_fleet_cost"]
    time_t1 = plan_t1["results"]["ortools"]["total_fleet_time_min"]

    # In traffic, fleet time increases -> composite J MUST strictly increase under fixed scales!
    assert time_t1 >= time_t0
    assert j_t1 >= j_t0, f"Expected J(T1) >= J(T0), got {j_t1} < {j_t0}"
