import json
import os
import pytest
from app.domain.graph import RoadGraph
from optimization.interfaces.optimizer import RoutingProblem
from optimization.baselines.dijkstra import DijkstraOptimizer
from optimization.metaheuristics.aco import ACOOptimizer
from optimization.quantum_inspired.qpso import QPSOOptimizer

@pytest.fixture
def bangalore_graph():
    current_dir = os.path.dirname(__file__)
    data_path = os.path.join(current_dir, "..", "data", "graphs", "sample_bangalore_network.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RoadGraph.from_dict(data)


def test_aco_solves_routing_problem(bangalore_graph):
    problem = RoutingProblem(
        graph_id="bangalore_silkboard_corridor",
        origin="1",
        destination="10",
        max_iterations=30,
        population_size=15,
        seed=42
    )
    aco = ACOOptimizer(num_ants=15)
    result = aco.solve(bangalore_graph, problem)
    
    assert result.is_feasible is True
    assert result.path[0] == "1"
    assert result.path[-1] == "10"
    assert result.cost > 0
    assert len(result.convergence_curve) == 30
    assert result.runtime_ms > 0


def test_qpso_solves_routing_problem(bangalore_graph):
    problem = RoutingProblem(
        graph_id="bangalore_silkboard_corridor",
        origin="1",
        destination="10",
        max_iterations=30,
        population_size=20,
        seed=42
    )
    qpso = QPSOOptimizer(num_particles=20)
    result = qpso.solve(bangalore_graph, problem)
    
    assert result.is_feasible is True
    assert result.path[0] == "1"
    assert result.path[-1] == "10"
    assert result.cost > 0
    assert len(result.convergence_curve) == 30
    assert result.runtime_ms > 0


def test_all_algorithms_avoid_closed_roads(bangalore_graph):
    # Origin: Silk Board (1), Dest: MG Road Trinity (10)
    problem = RoutingProblem(
        graph_id="bangalore_silkboard_corridor",
        origin="1",
        destination="10",
        max_iterations=30,
        population_size=15,
        seed=42
    )
    
    # Block the direct route segment 1 -> 2 (Silk Board to Koramangala)
    bangalore_graph.update_incident("1", "2", is_closed=True)
    
    dijkstra = DijkstraOptimizer()
    aco = ACOOptimizer(num_ants=15)
    qpso = QPSOOptimizer(num_particles=20)
    
    res_dijkstra = dijkstra.solve(bangalore_graph, problem)
    res_aco = aco.solve(bangalore_graph, problem)
    res_qpso = qpso.solve(bangalore_graph, problem)
    
    for res in [res_dijkstra, res_aco, res_qpso]:
        assert res.is_feasible is True
        for i in range(len(res.path) - 1):
            assert not (res.path[i] == "1" and res.path[i+1] == "2"), f"{res.algorithm_name} used closed edge!"
