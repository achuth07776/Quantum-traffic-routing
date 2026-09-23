import json
import os
import pytest
from app.domain.graph import RoadGraph
from optimization.interfaces.optimizer import RoutingProblem
from optimization.baselines.dijkstra import DijkstraOptimizer
from optimization.baselines.astar import AStarOptimizer

@pytest.fixture
def bangalore_graph():
    current_dir = os.path.dirname(__file__)
    data_path = os.path.join(current_dir, "..", "data", "graphs", "sample_bangalore_network.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RoadGraph.from_dict(data)


def test_dijkstra_finds_path_on_bangalore_graph(bangalore_graph):
    # Origin: Silk Board (1), Destination: MG Road Trinity Circle (10)
    problem = RoutingProblem(
        graph_id="bangalore_silkboard_corridor",
        origin="1",
        destination="10"
    )
    optimizer = DijkstraOptimizer()
    result = optimizer.solve(bangalore_graph, problem)
    
    assert result.is_feasible is True
    assert result.path[0] == "1"
    assert result.path[-1] == "10"
    assert result.distance_km > 0
    assert result.travel_time_min > 0
    assert result.runtime_ms >= 0


def test_astar_matches_dijkstra_path(bangalore_graph):
    problem = RoutingProblem(
        graph_id="bangalore_silkboard_corridor",
        origin="1",
        destination="10"
    )
    dijkstra = DijkstraOptimizer()
    astar = AStarOptimizer()
    
    res_dijkstra = dijkstra.solve(bangalore_graph, problem)
    res_astar = astar.solve(bangalore_graph, problem)
    
    assert res_dijkstra.is_feasible is True
    assert res_astar.is_feasible is True
    assert res_astar.path == res_dijkstra.path
    assert res_astar.cost == pytest.approx(res_dijkstra.cost, rel=1e-3)


def test_routing_reroutes_when_primary_road_is_closed(bangalore_graph):
    problem = RoutingProblem(
        graph_id="bangalore_silkboard_corridor",
        origin="1",
        destination="10"
    )
    dijkstra = DijkstraOptimizer()
    
    # 1. Normal route
    res_initial = dijkstra.solve(bangalore_graph, problem)
    initial_path = res_initial.path
    
    # 2. Close the first segment taken by the initial route
    u, v = initial_path[0], initial_path[1]
    bangalore_graph.update_incident(u, v, is_closed=True)
    
    # 3. Re-run Dijkstra
    res_rerouted = dijkstra.solve(bangalore_graph, problem)
    assert res_rerouted.is_feasible is True
    assert res_rerouted.path != initial_path
    assert res_rerouted.path[0] == "1"
    assert res_rerouted.path[-1] == "10"
    # Ensure closed edge is NOT in the rerouted path
    for i in range(len(res_rerouted.path) - 1):
        assert not (res_rerouted.path[i] == u and res_rerouted.path[i+1] == v)
