from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class FleetPlace(BaseModel):
    id: str = ""
    name: str
    address: str = ""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    provider_place_id: str = ""
    demand_kg: float = 0.0  # Must be > 0 for customers, 0 for depot


class FleetRequest(BaseModel):
    depot: FleetPlace
    customers: List[FleetPlace]
    num_vehicles: int = 3
    vehicle_capacity_kg: float = 500.0
    max_route_time_min: float = 240.0
    time_limit_seconds: int = 5
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"time": 0.7, "distance": 0.3}
    )


class CustomerStop(BaseModel):
    node_id: str
    name: str
    demand_kg: float = 100.0
    time_window_start_min: float = 0.0
    time_window_end_min: float = 180.0
    service_duration_min: float = 10.0

class VRPProblem(BaseModel):
    problem_id: str = "vizag_fleet_delivery_01"
    graph_id: str = "visakhapatnam_network"
    depot_node: str = "4"  # Maddilapalem RTC Hub Depot
    customers: List[CustomerStop]
    num_vehicles: int = 3
    vehicle_capacity_kg: float = 500.0
    max_route_time_min: float = 180.0  # HARD CONSTRAINT: Max allowable shift duration per vehicle
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"time": 0.5, "distance": 0.2, "congestion": 0.2, "emissions": 0.1}
    )
    max_iterations: int = 50
    population_size: int = 30
    seed: Optional[int] = 42

class VehicleRoute(BaseModel):
    vehicle_id: int
    customer_nodes: List[str]
    full_path_nodes: List[str]
    total_load_kg: float
    total_travel_time_min: float
    total_distance_km: float
    total_cost: float
    time_window_penalties: float = 0.0
    exceeds_max_route_time: bool = False
    is_feasible: bool = True

class VRPResult(BaseModel):
    algorithm_name: str
    routes: List[VehicleRoute]
    total_fleet_time_min: float
    total_fleet_distance_km: float
    total_fleet_cost: float
    unserved_customers: List[str] = Field(default_factory=list)
    optimality_gap_pct: Optional[float] = Field(
        default=None,
        description="Optimality gap percentage relative to exact solver (when exact benchmark is available)"
    )
    runtime_ms: float
    iterations: int = 0
    convergence_curve: List[float] = Field(default_factory=list)
    is_feasible: bool = True
    constraint_status: Dict[str, Any] = Field(
        default_factory=lambda: {
            "capacity_satisfied": True,
            "max_route_time_satisfied": True,
            "all_customers_served": True,
            "soft_time_window_penalties": 0.0
        }
    )
    provenance: Dict[str, str] = Field(
        default_factory=lambda: {
            "road_network": "CURATED REAL GEOGRAPHY (Visakhapatnam Coordinates)",
            "traffic": "SIMULATED (BPR Non-Linear Latency)",
            "cost": "DERIVED",
            "optimization": "OPTIMIZATION RESULT"
        }
    )
