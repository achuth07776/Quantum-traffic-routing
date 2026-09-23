import time
import random
import numpy as np
from typing import Dict, List, Set, Optional
from app.domain.graph import RoadGraph
from optimization.interfaces.optimizer import BaseOptimizer, RoutingProblem, OptimizationResult

class QPSOOptimizer(BaseOptimizer):
    """
    Quantum-Behaved Particle Swarm Optimization (QPSO) for dynamic multi-objective route optimization.
    
    Theoretical Framework:
    - Particle movement is modeled as quantum wave-function collapse in a delta-potential well.
    - Particles explore without velocity vectors, driven by the Mean Best (mbest) attractor and 
      dynamic Contraction-Expansion (CE) coefficient beta:
      X_i(t+1) = P_i +/- beta * |mbest - X_i(t)| * ln(1 / u)
    - Continuous quantum positions are mapped to discrete graph transitions via priority-guided 
      sub-graph exploration with cycle prevention.
    """
    def __init__(
        self,
        num_particles: int = 25,
        beta_max: float = 1.0,
        beta_min: float = 0.5,
        heuristic_weight: float = 1.5
    ):
        self.num_particles = num_particles
        self.beta_max = beta_max
        self.beta_min = beta_min
        self.heuristic_weight = heuristic_weight

    def _construct_path_from_particle(
        self,
        graph: RoadGraph,
        particle_pos: np.ndarray,
        node_to_idx: Dict[str, int],
        origin: str,
        destination: str,
        problem: RoutingProblem
    ) -> Optional[List[str]]:
        """
        Maps continuous quantum particle coordinate vector to a valid, cycle-free path on the graph.
        """
        path = [origin]
        visited: Set[str] = {origin}
        curr = origin
        max_steps = graph.graph.number_of_nodes() * 2
        
        while curr != destination and len(path) < max_steps:
            neighbors = [n for n in graph.get_neighbors(curr) if n not in visited]
            valid_candidates = []
            priorities = []
            
            for n in neighbors:
                metrics = graph.get_edge_metrics(curr, n, problem.weights)
                if metrics["is_closed"] or metrics["cost"] == float('inf'):
                    continue
                
                n_idx = node_to_idx.get(n, 0)
                # Quantum position priority + inverse cost heuristic
                base_quantum_priority = particle_pos[n_idx]
                cost_heuristic = 1.0 / max(0.001, metrics["cost"])
                score = base_quantum_priority + self.heuristic_weight * cost_heuristic
                
                valid_candidates.append(n)
                priorities.append(score)
                
            if not valid_candidates:
                return None
                
            # Pick neighbor with highest quantum-heuristic score
            best_idx = int(np.argmax(priorities))
            chosen = valid_candidates[best_idx]
            
            path.append(chosen)
            visited.add(chosen)
            curr = chosen
            
        return path if curr == destination else None

    def solve(self, graph: RoadGraph, problem: RoutingProblem) -> OptimizationResult:
        start_time = time.perf_counter()
        
        if problem.seed is not None:
            random.seed(problem.seed)
            np.random.seed(problem.seed)
            
        origin = str(problem.origin)
        destination = str(problem.destination)
        
        nodes_list = sorted(list(graph.nodes))
        num_nodes = len(nodes_list)
        node_to_idx = {node_id: i for i, node_id in enumerate(nodes_list)}
        
        if origin not in node_to_idx or destination not in node_to_idx:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return OptimizationResult(
                algorithm_name="Quantum-Behaved PSO (QPSO)",
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
            
        pop_size = max(10, min(self.num_particles, problem.population_size))
        max_iter = max(15, min(problem.max_iterations, 150))
        
        # Initialize quantum particle swarm in [-1.0, 1.0]^num_nodes
        particles = np.random.uniform(-1.0, 1.0, (pop_size, num_nodes))
        pbest_positions = np.copy(particles)
        pbest_costs = np.full(pop_size, float('inf'))
        pbest_paths: List[Optional[List[str]]] = [None] * pop_size
        
        gbest_position = np.zeros(num_nodes)
        gbest_cost = float('inf')
        gbest_path: Optional[List[str]] = None
        
        convergence_curve: List[float] = []
        
        # Initial evaluation
        for i in range(pop_size):
            path = self._construct_path_from_particle(graph, particles[i], node_to_idx, origin, destination, problem)
            if path:
                p_metrics = graph.get_path_metrics(path, problem.weights)
                if p_metrics["is_feasible"]:
                    pbest_costs[i] = p_metrics["cost"]
                    pbest_paths[i] = path
                    if p_metrics["cost"] < gbest_cost:
                        gbest_cost = p_metrics["cost"]
                        gbest_path = path
                        gbest_position = np.copy(particles[i])
                        
        # Main QPSO loop
        for t in range(max_iter):
            # Dynamic Contraction-Expansion (CE) coefficient beta
            beta = self.beta_max - (self.beta_max - self.beta_min) * (t / max_iter)
            
            # Compute Mean Best (mbest) position of swarm
            valid_pbest_indices = [idx for idx in range(pop_size) if pbest_costs[idx] < float('inf')]
            if valid_pbest_indices:
                mbest = np.mean(pbest_positions[valid_pbest_indices], axis=0)
            else:
                mbest = np.mean(pbest_positions, axis=0)
                
            for i in range(pop_size):
                phi = np.random.uniform(0.0, 1.0, num_nodes)
                # Local quantum attractor P_i
                p_attractor = phi * pbest_positions[i] + (1.0 - phi) * gbest_position
                
                u = np.random.uniform(0.0001, 0.9999, num_nodes)
                # Random sign (+1 or -1) for wave collapse
                sign = np.random.choice([-1.0, 1.0], size=num_nodes)
                
                # Quantum position update in delta-potential well
                particles[i] = p_attractor + sign * beta * np.abs(mbest - particles[i]) * np.log(1.0 / u)
                
                # Bounding position vector
                particles[i] = np.clip(particles[i], -3.0, 3.0)
                
                # Evaluate new position
                path = self._construct_path_from_particle(graph, particles[i], node_to_idx, origin, destination, problem)
                if path:
                    p_metrics = graph.get_path_metrics(path, problem.weights)
                    if p_metrics["is_feasible"] and p_metrics["cost"] < pbest_costs[i]:
                        pbest_costs[i] = p_metrics["cost"]
                        pbest_positions[i] = np.copy(particles[i])
                        pbest_paths[i] = path
                        
                        if p_metrics["cost"] < gbest_cost:
                            gbest_cost = p_metrics["cost"]
                            gbest_path = path
                            gbest_position = np.copy(particles[i])
                            
            convergence_curve.append(round(gbest_cost if gbest_cost < float('inf') else 0.0, 3))
            
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        if not gbest_path:
            return OptimizationResult(
                algorithm_name="Quantum-Behaved PSO (QPSO)",
                path=[],
                distance_km=0.0,
                travel_time_min=float('inf'),
                cost=float('inf'),
                emissions_g=float('inf'),
                runtime_ms=round(elapsed_ms, 3),
                iterations=max_iter,
                convergence_curve=convergence_curve,
                is_feasible=False,
                metadata={"error": "QPSO could not converge to a feasible path"}
            )
            
        final_metrics = graph.get_path_metrics(gbest_path, problem.weights)
        
        return OptimizationResult(
            algorithm_name="Quantum-Behaved PSO (QPSO)",
            path=gbest_path,
            distance_km=final_metrics["distance_km"],
            travel_time_min=final_metrics["travel_time_min"],
            cost=final_metrics["cost"],
            emissions_g=final_metrics["emissions_g"],
            runtime_ms=round(elapsed_ms, 3),
            iterations=max_iter,
            convergence_curve=convergence_curve,
            is_feasible=final_metrics["is_feasible"],
            metadata={
                "pop_size": pop_size,
                "beta_final": round(beta, 3),
                "quantum_model": "Delta-Potential Well"
            }
        )
