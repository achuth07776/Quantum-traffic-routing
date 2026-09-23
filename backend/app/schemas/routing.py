from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class OptimizeRouteRequest(BaseModel):
    graph_id: str = "visakhapatnam_network"
    origin_node: str = "1"
    destination_node: str = "6"
    algorithms: List[str] = Field(default_factory=lambda: ["dijkstra", "astar", "aco", "qpso"])
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"time": 0.5, "distance": 0.2, "congestion": 0.2, "emissions": 0.1}
    )
    max_iterations: int = 40
    population_size: int = 20
    seed: Optional[int] = 42

class SingleAlgorithmResultSchema(BaseModel):
    algorithm_name: str
    path: List[str]
    distance_km: float
    travel_time_min: float
    cost: float
    emissions_g: float
    runtime_ms: float
    iterations: int
    convergence_curve: List[float]
    is_feasible: bool
    path_geojson: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OptimizeRouteResponse(BaseModel):
    status: str
    graph_id: str
    origin_node: str
    destination_node: str
    baseline_algorithm: str
    results: Dict[str, SingleAlgorithmResultSchema]
    improvements: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Percentage improvements compared to baseline"
    )
    provenance: Dict[str, str] = Field(
        default_factory=lambda: {
            "road_network": "REAL DATA (OSM Visakhapatnam)",
            "traffic": "SIMULATED (BPR Engine)",
            "cost": "DERIVED",
            "optimization": "OPTIMIZATION RESULT",
            "emissions": "ESTIMATED"
        }
    )
    timestamp: str
