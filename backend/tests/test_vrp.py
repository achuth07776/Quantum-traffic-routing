import json
import os
import pytest
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem, CustomerStop
from optimization.vrp.vrp_baselines import GreedyVRP
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP

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
        problem_id="vizag_fleet_test",
        graph_id="visakhapatnam_network",
        depot_node="4",  # Maddilapalem
        customers=customers,
        num_vehicles=2,
        vehicle_capacity_kg=300.0,
        max_iterations=20,
        population_size=15,
        seed=42
    )

def test_greedy_vrp_solves_vizag_network(vizag_graph, vizag_vrp_problem):
    greedy = GreedyVRP()
    result = greedy.solve(vizag_graph, vizag_vrp_problem)
    
    assert len(result.routes) > 0
    assert result.is_feasible is True
    assert result.total_fleet_time_min > 0
    assert result.total_fleet_distance_km > 0
    assert len(result.unserved_customers) == 0

def test_qpso_vrp_solves_vizag_network(vizag_graph, vizag_vrp_problem):
    qpso_vrp = RandomKeyQPSOVRP(num_particles=15)
    result = qpso_vrp.solve(vizag_graph, vizag_vrp_problem)
    
    assert len(result.routes) > 0
    assert result.is_feasible is True
    assert result.total_fleet_time_min > 0
    assert result.total_fleet_cost > 0
    assert len(result.convergence_curve) == 20
    assert result.runtime_ms < 1000.0
