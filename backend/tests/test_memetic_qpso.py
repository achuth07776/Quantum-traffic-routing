"""
Tests for the Memetic Random-Key QPSO hybrid (QPSO + 2-Opt/Relocate Local Search).

Verifies:
1. The memetic hybrid solves the real Visakhapatnam VRP network.
2. On identical paired instances the hybrid is NEVER worse than vanilla QPSO.
3. The hybrid is strictly deterministic under a fixed seed.
4. The matrix-level RealWorldVRPOptimizer memetic hook (qpso_memetic=True) is
   reproducible under a fixed seed.
"""
import json
import os
import pytest
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem, CustomerStop
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP
from optimization.vrp.vrp_qpso_memetic import MemeticRandomKeyQPSOVRP
from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer


@pytest.fixture
def vizag_graph():
    current_dir = os.path.dirname(__file__)
    data_path = os.path.join(current_dir, "..", "data", "graphs", "visakhapatnam_network.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RoadGraph.from_dict(data)


@pytest.fixture
def vizag_vrp_problem():
    customers = [
        CustomerStop(node_id="1", name="RK Beach Tourist Depot", demand_kg=100.0, time_window_start_min=10.0, time_window_end_min=120.0),
        CustomerStop(node_id="2", name="Siripuram AU Complex", demand_kg=80.0, time_window_start_min=0.0, time_window_end_min=90.0),
        CustomerStop(node_id="3", name="Jagadamba Commercial Store", demand_kg=120.0, time_window_start_min=15.0, time_window_end_min=150.0),
        CustomerStop(node_id="5", name="MVP Colony Delivery Hub", demand_kg=90.0, time_window_start_min=0.0, time_window_end_min=100.0),
        CustomerStop(node_id="6", name="Rushikonda Tech Park", demand_kg=110.0, time_window_start_min=30.0, time_window_end_min=180.0)
    ]
    return VRPProblem(
        problem_id="vizag_fleet_memetic_test",
        graph_id="visakhapatnam_network",
        depot_node="4",  # Maddilapalem
        customers=customers,
        num_vehicles=2,
        vehicle_capacity_kg=300.0,
        max_iterations=20,
        population_size=15,
        seed=42
    )


def test_memetic_vrp_solves_vizag_network(vizag_graph, vizag_vrp_problem):
    memetic = MemeticRandomKeyQPSOVRP(num_particles=15)
    result = memetic.solve(vizag_graph, vizag_vrp_problem)

    assert len(result.routes) > 0
    assert result.is_feasible is True
    assert result.total_fleet_time_min > 0
    assert result.total_fleet_cost > 0
    assert len(result.convergence_curve) == 20
    assert result.runtime_ms < 2000.0


def test_memetic_at_least_as_good_as_vanilla_on_fixed_instance(vizag_graph, vizag_vrp_problem):
    # Empirical regression guard on a fixed deterministic instance: the memetic
    # hybrid starts from the same swarm seed and polishes gbest with local
    # search, so it must never be worse here. (Feedback can alter later swarm
    # exploration in general, so this is checked on the fixed instance, not
    # claimed universally.)
    vanilla = RandomKeyQPSOVRP(num_particles=15)
    memetic = MemeticRandomKeyQPSOVRP(num_particles=15)

    v_res = vanilla.solve(vizag_graph, vizag_vrp_problem)
    m_res = memetic.solve(vizag_graph, vizag_vrp_problem)

    assert m_res.is_feasible == v_res.is_feasible
    assert m_res.total_fleet_cost <= v_res.total_fleet_cost + 1e-6
    assert m_res.total_fleet_time_min <= v_res.total_fleet_time_min + 1e-6


def test_memetic_same_seed_identical_reproducibility(vizag_graph, vizag_vrp_problem):
    memetic = MemeticRandomKeyQPSOVRP(num_particles=15)

    run1 = memetic.solve(vizag_graph, vizag_vrp_problem)
    run2 = memetic.solve(vizag_graph, vizag_vrp_problem)

    assert abs(run1.total_fleet_cost - run2.total_fleet_cost) < 1e-6
    routes1 = [r.customer_nodes for r in run1.routes]
    routes2 = [r.customer_nodes for r in run2.routes]
    assert routes1 == routes2


@pytest.fixture
def matrix_vrp_setup():
    node_ids = ["depot", "s1", "s2", "s3", "s4"]
    durations = [
        [0.0, 12.0, 18.0, 24.0, 30.0],
        [12.0, 0.0, 10.0, 15.0, 20.0],
        [18.0, 10.0, 0.0, 12.0, 16.0],
        [24.0, 15.0, 12.0, 0.0, 14.0],
        [30.0, 20.0, 16.0, 14.0, 0.0]
    ]
    distances = [
        [0.0, 6.0, 9.0, 12.0, 15.0],
        [6.0, 0.0, 5.0, 8.0, 10.0],
        [9.0, 5.0, 0.0, 6.0, 8.0],
        [12.0, 8.0, 6.0, 0.0, 7.0],
        [15.0, 10.0, 8.0, 7.0, 0.0]
    ]
    demands = [0.0, 40.0, 50.0, 30.0, 60.0]
    capacities = [150.0, 150.0]
    return node_ids, durations, distances, demands, capacities


def test_matrix_memetic_hook_reproducible(matrix_vrp_setup):
    node_ids, durations, distances, demands, capacities = matrix_vrp_setup
    optimizer = RealWorldVRPOptimizer()

    run1 = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        depot_index=0,
        qpso_particles=20,
        qpso_iterations=30,
        qpso_seed=2024,
        qpso_memetic=True
    )
    run2 = optimizer.solve_fleet_vrp(
        node_ids=node_ids,
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        depot_index=0,
        qpso_particles=20,
        qpso_iterations=30,
        qpso_seed=2024,
        qpso_memetic=True
    )

    q1 = run1["results"]["qpso"]
    q2 = run2["results"]["qpso"]

    assert abs(q1["total_fleet_cost"] - q2["total_fleet_cost"]) < 1e-6
    routes1 = [r.get("customer_nodes", []) if isinstance(r, dict) else r.customer_nodes for r in q1["routes"]]
    routes2 = [r.get("customer_nodes", []) if isinstance(r, dict) else r.customer_nodes for r in q2["routes"]]
    assert routes1 == routes2