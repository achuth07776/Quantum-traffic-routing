import time
import random
import numpy as np
from typing import Dict, List, Set, Optional, Tuple
from app.domain.graph import RoadGraph
from optimization.interfaces.optimizer import BaseOptimizer, RoutingProblem, OptimizationResult

class ACOOptimizer(BaseOptimizer):
    """
    Ant Colony Optimization (ACO) for dynamic multi-objective route optimization.
    Features:
    - Pheromone matrix updated dynamically with evaporation.
    - Heuristic attraction inversely proportional to dynamic BPR travel time and congestion.
    - Cycle-prevention mechanism (tabu list per ant).
    - Elitist pheromone reinforcement for the iteration-best and global-best ants.
    """
    def __init__(
        self,
        num_ants: int = 20,
        alpha: float = 1.0,  # Pheromone importance
        beta: float = 2.0,   # Heuristic importance
        rho: float = 0.1,    # Evaporation rate
        q: float = 100.0,    # Pheromone deposit factor
        initial_pheromone: float = 1.0
    ):
        self.num_ants = num_ants
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.initial_pheromone = initial_pheromone

    def solve(self, graph: RoadGraph, problem: RoutingProblem) -> OptimizationResult:
        start_time = time.perf_counter()
        
        if problem.seed is not None:
            random.seed(problem.seed)
            np.random.seed(problem.seed)
            
        origin = str(problem.origin)
        destination = str(problem.destination)
        
        if origin not in graph.nodes or destination not in graph.nodes:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return OptimizationResult(
                algorithm_name="Ant Colony Optimization (ACO)",
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
            
        # Initialize pheromone table: Dict[(u, v), float]
        pheromones: Dict[Tuple[str, str], float] = {}
        for u, v in graph.edges:
            pheromones[(u, v)] = self.initial_pheromone
            
        max_iter = max(10, min(problem.max_iterations, 150))
        num_ants = max(5, min(self.num_ants, problem.population_size))
        
        best_path: Optional[List[str]] = None
        best_cost: float = float('inf')
        convergence_curve: List[float] = []
        
        for iteration in range(max_iter):
            iteration_paths: List[Tuple[List[str], float]] = []
            
            for ant in range(num_ants):
                path = [origin]
                visited: Set[str] = {origin}
                curr = origin
                stuck = False
                
                while curr != destination:
                    neighbors = [n for n in graph.get_neighbors(curr) if n not in visited]
                    
                    # Filter out closed roads or infinite cost edges
                    valid_neighbors = []
                    probabilities = []
                    
                    for n in neighbors:
                        metrics = graph.get_edge_metrics(curr, n, problem.weights)
                        if metrics["is_closed"] or metrics["cost"] == float('inf'):
                            continue
                        
                        tau = pheromones.get((curr, n), self.initial_pheromone)
                        # Heuristic attractiveness: eta = 1 / cost
                        eta = 1.0 / max(0.001, metrics["cost"])
                        
                        prob_weight = (tau ** self.alpha) * (eta ** self.beta)
                        valid_neighbors.append(n)
                        probabilities.append(prob_weight)
                        
                    if not valid_neighbors:
                        stuck = True
                        break
                        
                    prob_sum = sum(probabilities)
                    if prob_sum <= 0:
                        chosen_next = random.choice(valid_neighbors)
                    else:
                        normalized_probs = [p / prob_sum for p in probabilities]
                        chosen_next = np.random.choice(valid_neighbors, p=normalized_probs)
                        
                    path.append(chosen_next)
                    visited.add(chosen_next)
                    curr = chosen_next
                    
                    # Prevent runaway exploration
                    if len(path) > graph.graph.number_of_nodes() * 2:
                        stuck = True
                        break
                        
                if not stuck and curr == destination:
                    p_metrics = graph.get_path_metrics(path, problem.weights)
                    if p_metrics["is_feasible"] and p_metrics["cost"] < float('inf'):
                        iteration_paths.append((path, p_metrics["cost"]))
                        if p_metrics["cost"] < best_cost:
                            best_cost = p_metrics["cost"]
                            best_path = path
                            
            # Pheromone evaporation
            for edge in pheromones:
                pheromones[edge] = max(0.01, (1.0 - self.rho) * pheromones[edge])
                
            # Pheromone reinforcement for successful ants
            for path, cost in iteration_paths:
                deposit = self.q / max(0.01, cost)
                for i in range(len(path) - 1):
                    e = (path[i], path[i+1])
                    if e in pheromones:
                        pheromones[e] += deposit
                        
            # Elitist reinforcement for global best
            if best_path:
                elite_deposit = (2.0 * self.q) / max(0.01, best_cost)
                for i in range(len(best_path) - 1):
                    e = (best_path[i], best_path[i+1])
                    if e in pheromones:
                        pheromones[e] += elite_deposit
                        
            convergence_curve.append(round(best_cost if best_cost < float('inf') else 0.0, 3))
            
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        if not best_path:
            return OptimizationResult(
                algorithm_name="Ant Colony Optimization (ACO)",
                path=[],
                distance_km=0.0,
                travel_time_min=float('inf'),
                cost=float('inf'),
                emissions_g=float('inf'),
                runtime_ms=round(elapsed_ms, 3),
                iterations=max_iter,
                convergence_curve=convergence_curve,
                is_feasible=False,
                metadata={"error": "No feasible path discovered by ants"}
            )
            
        final_metrics = graph.get_path_metrics(best_path, problem.weights)
        
        return OptimizationResult(
            algorithm_name="Ant Colony Optimization (ACO)",
            path=best_path,
            distance_km=final_metrics["distance_km"],
            travel_time_min=final_metrics["travel_time_min"],
            cost=final_metrics["cost"],
            emissions_g=final_metrics["emissions_g"],
            runtime_ms=round(elapsed_ms, 3),
            iterations=max_iter,
            convergence_curve=convergence_curve,
            is_feasible=final_metrics["is_feasible"],
            metadata={
                "num_ants": num_ants,
                "evaporation_rate": self.rho,
                "alpha": self.alpha,
                "beta": self.beta
            }
        )
