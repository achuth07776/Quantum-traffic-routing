from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RoutingProblem(BaseModel):
    graph_id: str = "default"
    origin: str
    destination: str
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"time": 0.5, "distance": 0.2, "congestion": 0.2, "emissions": 0.1}
    )
    max_iterations: int = 100
    population_size: int = 30
    seed: Optional[int] = 42

class OptimizationResult(BaseModel):
    algorithm_name: str
    path: List[str]
    distance_km: float
    travel_time_min: float
    cost: float
    emissions_g: float
    runtime_ms: float
    iterations: int = 0
    convergence_curve: List[float] = Field(default_factory=list)
    is_feasible: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseOptimizer(ABC):
    @abstractmethod
    def solve(self, graph: Any, problem: RoutingProblem) -> OptimizationResult:
        """
        Solves the routing problem on the provided graph and returns a standardized OptimizationResult.
        """
