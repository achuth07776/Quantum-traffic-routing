import time
import heapq
from typing import Dict, List, Tuple, Optional
from app.domain.graph import RoadGraph
from optimization.interfaces.optimizer import BaseOptimizer, RoutingProblem, OptimizationResult

class AStarOptimizer(BaseOptimizer):
    """
    A* Shortest-Travel-Time Baseline Optimizer.
    Uses Haversine physical coordinate distance divided by maximum speed limit
    as a mathematically admissible lower-bound heuristic for travel time:
    h(n) = (Haversine(n, dest) / max_speed_kmh) * 60  [minutes]
    """
    def __init__(self, max_speed_kmh: float = 80.0):
        self.max_speed_kmh = max_speed_kmh

    def _heuristic(self, graph: RoadGraph, curr_node: str, dest_node: str) -> float:
        """
        Admissible heuristic lower bound:
        Distance (km) / MaxSpeed (km/h) * 60 = minimum possible travel time (min).
        """
        dist_km = graph.get_haversine_distance(curr_node, dest_node)
        return (dist_km / self.max_speed_kmh) * 60.0

    def solve(self, graph: RoadGraph, problem: RoutingProblem) -> OptimizationResult:
        start_time = time.perf_counter()
        
        origin = str(problem.origin)
        destination = str(problem.destination)
        
        if origin not in graph.nodes or destination not in graph.nodes:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return OptimizationResult(
                algorithm_name="A* (Travel-Time Baseline)",
                path=[],
                distance_km=0.0,
                travel_time_min=float('inf'),
                cost=float('inf'),
                emissions_g=float('inf'),
                runtime_ms=round(elapsed_ms, 3),
                iterations=0,
                is_feasible=False,
                metadata={"error": "Origin or Destination node not found"}
            )
            
        # Priority Queue: (f_score, g_score_time, curr_node, path)
        h_start = self._heuristic(graph, origin, destination)
        pq: List[Tuple[float, float, str, List[str]]] = [(h_start, 0.0, origin, [origin])]
        g_scores_time: Dict[str, float] = {origin: 0.0}
        iterations = 0
        found_path: Optional[List[str]] = None
        
        while pq:
            f_score, g_time, curr_node, path = heapq.heappop(pq)
            iterations += 1
            
            if curr_node == destination:
                found_path = path
                break
                
            if g_time > g_scores_time.get(curr_node, float('inf')):
                continue
                
            for neighbor in graph.get_neighbors(curr_node):
                metrics = graph.get_edge_metrics(curr_node, neighbor, problem.weights)
                
                if metrics["is_closed"] or metrics["cost"] == float('inf'):
                    continue
                    
                edge_time = metrics["travel_time_min"]
                tentative_g = g_time + edge_time
                
                if tentative_g < g_scores_time.get(neighbor, float('inf')):
                    g_scores_time[neighbor] = tentative_g
                    h_neighbor = self._heuristic(graph, neighbor, destination)
                    f_neighbor = tentative_g + h_neighbor
                    heapq.heappush(pq, (f_neighbor, tentative_g, neighbor, path + [neighbor]))
                    
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        if not found_path:
            return OptimizationResult(
                algorithm_name="A* (Travel-Time Baseline)",
                path=[],
                distance_km=0.0,
                travel_time_min=float('inf'),
                cost=float('inf'),
                emissions_g=float('inf'),
                runtime_ms=round(elapsed_ms, 3),
                iterations=iterations,
                is_feasible=False,
                metadata={"error": "No feasible route found"}
            )
            
        path_metrics = graph.get_path_metrics(found_path, problem.weights)
        
        return OptimizationResult(
            algorithm_name="A* (Travel-Time Baseline)",
            path=found_path,
            distance_km=path_metrics["distance_km"],
            travel_time_min=path_metrics["travel_time_min"],
            cost=path_metrics["cost"],
            emissions_g=path_metrics["emissions_g"],
            runtime_ms=round(elapsed_ms, 3),
            iterations=iterations,
            convergence_curve=[path_metrics["cost"]],
            is_feasible=path_metrics["is_feasible"],
            metadata={"nodes_explored": len(g_scores_time)}
        )
