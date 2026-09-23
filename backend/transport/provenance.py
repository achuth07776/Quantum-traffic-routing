"""Data provenance tracker."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

class ProvenanceMetadata(BaseModel):
    routing_provider: str
    traffic_source: str
    traffic_age_seconds: float
    network_source: str
    last_updated: str

class DataProvenanceTracker:
    def __init__(self):
        self.routing_provider = "unknown"
        self.traffic_source = "none"
        self.network_source = "osm"
        self.traffic_timestamp: Optional[datetime] = None
        self.confidence_level: float = 1.0

    def update_routing_provider(self, provider: str):
        self.routing_provider = provider

    def update_traffic_source(self, source: str, timestamp: Optional[datetime] = None, confidence: float = 1.0):
        self.traffic_source = source
        self.traffic_timestamp = timestamp or datetime.now(timezone.utc)
        self.confidence_level = confidence

    def update_network_source(self, source: str):
        self.network_source = source

    def generate_metadata(self) -> ProvenanceMetadata:
        age_seconds = 0.0
        if self.traffic_timestamp:
            age_seconds = (datetime.now(timezone.utc) - self.traffic_timestamp).total_seconds()
            
        return ProvenanceMetadata(
            routing_provider=self.routing_provider,
            traffic_source=self.traffic_source,
            traffic_age_seconds=max(0.0, age_seconds),
            network_source=self.network_source,
            last_updated=datetime.now(timezone.utc).isoformat()
        )

    def get_metadata(self) -> dict:
        return self.generate_metadata().model_dump()
