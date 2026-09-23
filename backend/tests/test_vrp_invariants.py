"""
Test VRP Invariants: Capacity and Customer Partition Correctness.

Verifies:
1. Every customer is served exactly once across all vehicle routes (no omission, no duplicate).
2. Vehicle capacity limits are strictly respected for every vehicle.
3. Capacity overload scenarios are correctly flagged as infeasible.
"""
import pytest
from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer


@pytest.fixture
def sample_vrp_matrix():
    """5-node symmetric travel time and distance matrix (Depot + 4 customers)."""
    node_ids = ["depot", "c1", "c2", "c3", "c4"]
    durations = [
        [0.0, 10.0, 15.0, 20.0, 25.0],
        [10.0, 0.0, 12.0, 18.0, 22.0],
        [15.0, 12.0, 0.0, 14.0, 16.0],
        [20.0, 18.0, 14.0, 0.0, 11.0],
        [25.0, 22.0, 16.0, 11.0, 0.0]
    ]
    distances = [
        [0.0, 5.0, 8.0, 10.0, 12.0],
        [5.0, 0.0, 6.0, 9.0, 11.0],
        [8.0, 6.0, 0.0, 7.0, 8.0],
        [10.0, 9.0, 7.0, 0.0, 5.0],
        [12.0, 11.0, 8.0, 5.0, 0.0]
    ]
    return node_ids, durations, distances


def test_vrp_all_customers_visited_exactly_once(sample_vrp_matrix):
    """Verify that all customers are visited exactly once across OR-Tools, QPSO, and Greedy."""
    node_ids, durations, distances = sample_vrp_matrix
    expected_customers = set(node_ids[1:])
    demands = [0.0, 50.0, 60.0, 70.0, 80.0]
    capacities = [200.0, 200.0]

    optimizer = RealWorldVRPOptimizer()
    output = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        depot_index=0,
        time_limit_seconds=1.0,
        qpso_particles=30,
        qpso_iterations=40,
        qpso_seed=42
    )

    for solver_key in ["ortools", "qpso", "greedy"]:
        res = output["results"][solver_key]
        assert res["is_feasible"] is True, f"{solver_key} failed to find feasible solution"

        visited_customers = []
        for r in res["routes"]:
            cust_nodes = r.get("customer_nodes", []) if isinstance(r, dict) else r.customer_nodes
            visited_customers.extend(cust_nodes)

        # 1. No customer omitted
        assert set(visited_customers) == expected_customers, (
            f"{solver_key} visited {set(visited_customers)}, expected {expected_customers}"
        )
        # 2. No customer visited more than once
        assert len(visited_customers) == len(expected_customers), (
            f"{solver_key} visited {len(visited_customers)} stops, expected {len(expected_customers)}"
        )


def test_vrp_vehicle_capacity_strictly_respected(sample_vrp_matrix):
    """Verify that each vehicle load does not exceed its rated capacity."""
    node_ids, durations, distances = sample_vrp_matrix
    demands = [0.0, 80.0, 90.0, 70.0, 60.0]
    max_cap = 180.0
    capacities = [max_cap, max_cap]
    demand_map = dict(zip(node_ids, demands))

    optimizer = RealWorldVRPOptimizer()
    output = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        depot_index=0,
        time_limit_seconds=1.0,
        qpso_particles=30,
        qpso_iterations=40,
        qpso_seed=42
    )

    for solver_key in ["ortools", "qpso", "greedy"]:
        res = output["results"][solver_key]
        for r in res["routes"]:
            cust_nodes = r.get("customer_nodes", []) if isinstance(r, dict) else r.customer_nodes
            route_load = sum(demand_map[c] for c in cust_nodes)
            assert route_load <= max_cap, (
                f"{solver_key} vehicle exceeded capacity: load {route_load} > {max_cap}"
            )


def test_vrp_capacity_overload_rejection(sample_vrp_matrix):
    """Verify that impossible capacity requests are flagged as infeasible or leave unserved stops."""
    node_ids, durations, distances = sample_vrp_matrix
    # Total demand = 400 kg, total fleet capacity = 100 kg
    demands = [0.0, 100.0, 100.0, 100.0, 100.0]
    tiny_capacities = [50.0, 50.0]

    optimizer = RealWorldVRPOptimizer()
    output = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=tiny_capacities,
        depot_index=0,
        time_limit_seconds=1.0,
        qpso_particles=20,
        qpso_iterations=20,
        qpso_seed=42
    )

    # At least one solver must flag infeasibility or unserved customers
    ortools_feas = output["results"]["ortools"]["is_feasible"]
    greedy_unserved = output["results"]["greedy"]["unserved_customers"]
    assert (not ortools_feas) or (len(greedy_unserved) > 0), (
        "Overloaded problem must not be marked fully feasible without unserved customers"
    )
