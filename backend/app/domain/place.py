"""
Canonical Place Resolution Model.

Represents a single authoritative place resolved through provider metadata (TomTom)
and verified against the road network access point via OSRM nearest snapping.
"""

from typing import Optional
from pydantic import BaseModel, Field


class PlaceResolution(BaseModel):
    """
    Canonical, auditable place resolution object used across all routing operations.
    Guarantees that routing occurs from drivable access points rather than raw parcel centroids.
    """
    provider: str = "TomTom"
    provider_place_id: str = ""
    name: str
    address: str = ""
    category: Optional[str] = "place"
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Raw place centroid latitude from provider")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Raw place centroid longitude from provider")
    access_latitude: float = Field(..., ge=-90.0, le=90.0, description="Validated drivable road access latitude")
    access_longitude: float = Field(..., ge=-180.0, le=180.0, description="Validated drivable road access longitude")
    access_road_name: str = Field(default="Unnamed road", description="Drivable road / way name at the access point")
    snap_distance_m: float = Field(default=0.0, ge=0.0, description="Orthogonal snap distance from place/entry to road")
    resolution_method: str = Field(default="OSRM_NEAREST", description="Method used: TOMTOM_ENTRY_POINT, OSRM_NEAREST, DIRECT")
    confidence: str = Field(default="HIGH", description="Confidence tier: HIGH (<=50m), MEDIUM (50-150m), REVIEW (150-500m), INVALID (>500m)")
    entry_points_available: int = Field(default=0, ge=0, description="Number of candidate vehicle entry points provided by TomTom")
