import time
import heapq
from typing import Dict, List, Tuple, Optional
from app.domain.graph import RoadGraph
from optimization.interfaces.optimizer import BaseOptimizer, RoutingProblem, OptimizationResult

class DijkstraOptimizer(BaseOptimizer):
    """
    Exact single-source shortest path baseline using Dijkstra's algorithm
    evaluated on the dynamic BPR multi-objective cost function.
    """
    def __init__(self, optimize_for: str = "cost"):
        self.optimize_for = optimize_for  # "cost" or "time"

    def solve(self, graph: RoadGraph, problem: RoutingProblem) -> OptimizationResult:
        start_time = time.perf_counter()
        
        origin = str(problem.origin)
        destination = str(problem.destination)
        
        if origin not in graph.nodes or destination not in graph.nodes:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return OptimizationResult(
                algorithm_name="Dijkstra (Baseline)",
                path=[],
                distance_km=0.0,
                travel_time_min=float('inf'),
                cost=float('inf'),
                emissions_g=float('inf'),
                runtime_ms=round(elapsed_ms, 3),
                iterations=0,
                is_feasible=False,
                metadata={"error": "Origin or Destination node not found in graph"}
            )
            
        # Priority Queue: (current_cost, current_node, path)
        pq: List[Tuple[float, str, List[str]]] = [(0.0, origin, [origin])]
        best_costs: Dict[str, float] = {origin: 0.0}
        iterations = 0
        
        found_path: Optional[List[str]] = None
        
        while pq:
            curr_cost, curr_node, path = heapq.heappop(pq)
            iterations += 1
            
            if curr_node == destination:
                found_path = path
                break
                
            if curr_cost > best_costs.get(curr_node, float('inf')):
                continue
                
            for neighbor in graph.get_neighbors(curr_node):
                metrics = graph.get_edge_metrics(curr_node, neighbor, problem.weights)
                
                if metrics["is_closed"] or metrics["cost"] == float('inf'):
                    continue
                    
                edge_cost = metrics["travel_time_min"] if self.optimize_for == "time" else metrics["cost"]
                new_cost = curr_cost + edge_cost
                
                if new_cost < best_costs.get(neighbor, float('inf')):
                    best_costs[neighbor] = new_cost
                    heapq.heappush(pq, (new_cost, neighbor, path + [neighbor]))
                    
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        if not found_path:
            return OptimizationResult(
                algorithm_name="Dijkstra (Baseline)",
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
            algorithm_name="Dijkstra (Baseline)",
            path=found_path,
            distance_km=path_metrics["distance_km"],
            travel_time_min=path_metrics["travel_time_min"],
            cost=path_metrics["cost"],
            emissions_g=path_metrics["emissions_g"],
            runtime_ms=round(elapsed_ms, 3),
            iterations=iterations,
            convergence_curve=[path_metrics["cost"]],
            is_feasible=path_metrics["is_feasible"],
            metadata={"nodes_explored": len(best_costs)}
        )
