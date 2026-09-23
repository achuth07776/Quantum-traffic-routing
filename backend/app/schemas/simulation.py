from typing import List, Dict, Any
from pydantic import BaseModel, Field

class IncidentInjectionRequest(BaseModel):
    graph_id: str = "bangalore_silkboard_corridor"
    u: str
    v: str
    incident_type: str = Field(
        default="ROAD_BLOCK",
        description="Type: ROAD_BLOCK, BOTTLENECK_SPIKE, SPEED_REDUCTION"
    )
    multiplier: float = 2.5
    is_closed: bool = True

class IncidentInjectionResponse(BaseModel):
    status: str
    u: str
    v: str
    is_closed: bool
    incident_multiplier: float
    updated_edge_metrics: Dict[str, Any]

class ScenarioPreset(BaseModel):
    scenario_id: str
    title: str
    description: str
    city: str
    origin_node: str
    destination_node: str
    incidents: List[IncidentInjectionRequest]
