from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Coords(BaseModel):
    lat: float
    lon: float

class RouteStep(BaseModel):
    instruction: str
    road_name: str
    distance_m: float
    duration_s: float

class RouteResult(BaseModel):
    provider: str
    distance_m: float
    duration_s: float
    geometry_geojson: Dict[str, Any]  # GeoJSON LineString
    steps: List[RouteStep] = []
    raw_metadata: Dict[str, Any] = {}

class TravelTimeMatrix(BaseModel):
    provider: str
    durations_s: List[List[float]]  # NxN matrix
    distances_m: List[List[float]]  # NxN matrix
    locations: List[Coords]

class SnappedPoint(BaseModel):
    original: Coords
    snapped: Coords
    road_name: str = ""
    distance_m: float = 0.0

class BaseRoutingProvider(ABC):
    @abstractmethod
    async def route(self, origin: Coords, destination: Coords, alternatives: bool = False) -> List[RouteResult]: ...
    
    @abstractmethod
    async def table(self, locations: List[Coords]) -> TravelTimeMatrix: ...
    
    @abstractmethod
    async def nearest(self, point: Coords) -> Optional[SnappedPoint]: ...
    
    @abstractmethod
    async def health_check(self) -> bool: ...
