"""Base interfaces for traffic providers."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from pydantic import BaseModel

class TrafficObservation(BaseModel):
    segment_id: str
    speed_kmh: float
    free_flow_speed_kmh: float
    jam_factor: float  # 0.0 = free flow, 10.0 = standstill
    confidence: float  # 0.0 to 1.0
    observed_at: str  # ISO 8601
    source: str

class IncidentReport(BaseModel):
    incident_id: str
    type: str  # ROAD_CLOSURE, CONGESTION, CONSTRUCTION, ACCIDENT
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    lat: float
    lon: float
    description: str
    start_time: str
    expected_end_time: Optional[str] = None
    source: str = "TomTom"
    delay_seconds: float = 0.0
    length_meters: float = 0.0

class TrafficSnapshot(BaseModel):
    provider: str
    observed_at: str
    segments_updated: int
    observations: List[TrafficObservation]
    incidents: List[IncidentReport]
    source_status: str  # LIVE, STALE, FALLBACK, UNAVAILABLE
    raw_observations_count: int = 0
    mapped_segments_count: int = 0
    traffic_source_type: str = "FALLBACK"  # LIVE_PROVIDER, FALLBACK_BPR, WHAT_IF_SCENARIO

class BaseTrafficProvider(ABC):
    @abstractmethod
    async def get_flow(self, bbox: Tuple[float, float, float, float]) -> TrafficSnapshot: ...
    
    @abstractmethod  
    async def get_incidents(self, bbox: Tuple[float, float, float, float]) -> List[IncidentReport]: ...
    
    @abstractmethod
    async def health_check(self) -> bool: ...
