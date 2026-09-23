import os
import json
import pytest
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem, CustomerStop
from optimization.vrp.exact_vrp import ExactVRP
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP
from experiments.statistics import compute_trial_statistics
from experiments.synthetic_generator import generate_synthetic_road_network

@pytest.fixture
def sample_problem():
    customers = [
        CustomerStop(node_id="1", name="Stop 1", demand_kg=60.0, time_window_start_min=0.0, time_window_end_min=120.0),
        CustomerStop(node_id="2", name="Stop 2", demand_kg=80.0, time_window_start_min=0.0, time_window_end_min=90.0),
        CustomerStop(node_id="3", name="Stop 3", demand_kg=100.0, time_window_start_min=0.0, time_window_end_min=150.0),
        CustomerStop(node_id="5", name="Stop 5", demand_kg=90.0, time_window_start_min=0.0, time_window_end_min=100.0)
    ]
    return VRPProblem(
        problem_id="exact_test_p1",
        graph_id="visakhapatnam_network",
        depot_node="4",
        customers=customers,
        num_vehicles=2,
        vehicle_capacity_kg=300.0,
        max_route_time_min=180.0
    )

def test_exact_vrp_matches_or_beats_qpso(sample_problem):
    vizag_path = os.path.join(os.path.dirname(__file__), "..", "data", "graphs", "visakhapatnam_network.json")
    with open(vizag_path, "r", encoding="utf-8") as f:
        vizag_data = json.load(f)
    graph = RoadGraph.from_dict(vizag_data)
    
    exact = ExactVRP()
    exact_res = exact.solve(graph, sample_problem)
    
    qpso = RandomKeyQPSOVRP(num_particles=25)
    qpso_res = qpso.solve(graph, sample_problem)
    
    assert exact_res.is_feasible is True
    assert exact_res.total_fleet_cost > 0
    # Exact cost must be <= QPSO cost (global minimum)
    assert exact_res.total_fleet_cost <= qpso_res.total_fleet_cost + 1e-3

def test_synthetic_network_generator():
    synth_graph = generate_synthetic_road_network(num_nodes=20, seed=42)
    assert synth_graph.graph.number_of_nodes() == 20
    assert synth_graph.graph.number_of_edges() >= 30

def test_statistics_calculator():
    runs = [
        {"total_fleet_cost": 20.0, "total_fleet_time_min": 30.0, "runtime_ms": 15.0, "is_feasible": True, "optimality_gap_pct": 0.0},
        {"total_fleet_cost": 22.0, "total_fleet_time_min": 32.0, "runtime_ms": 18.0, "is_feasible": True, "optimality_gap_pct": 10.0}
    ]
    stats = compute_trial_statistics(runs)
    assert stats["num_trials"] == 2
    assert stats["feasibility_rate_pct"] == 100.0
    assert stats["mean_cost"] == 21.0
    assert stats["best_cost"] == 20.0
    assert stats["mean_optimality_gap_pct"] == 5.0
