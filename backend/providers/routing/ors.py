import os
import httpx
import logging
from typing import List
from .base import BaseRoutingProvider, Coords, RouteResult, RouteStep, TravelTimeMatrix, SnappedPoint

logger = logging.getLogger(__name__)

class ORSRoutingProvider(BaseRoutingProvider):
    def __init__(self, api_key: str = "", base_url: str = "https://api.openrouteservice.org"):
        self.api_key = api_key or os.getenv("ORS_API_KEY", "")
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = self.api_key
    
    async def route(self, origin: Coords, destination: Coords, alternatives: bool = False) -> List[RouteResult]:
        url = f"{self.base_url}/v2/directions/driving-car/geojson"
        payload = {
            "coordinates": [[origin.lon, origin.lat], [destination.lon, destination.lat]]
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for feature in data.get("features", []):
                    geometry = feature.get("geometry", {})
                    properties = feature.get("properties", {})
                    summary = properties.get("summary", {})
                    segments = properties.get("segments", [])
                    
                    steps = []
                    for segment in segments:
                        for step in segment.get("steps", []):
                            steps.append(RouteStep(
                                instruction=step.get("instruction", ""),
                                road_name=step.get("name", ""),
                                distance_m=step.get("distance", 0.0),
                                duration_s=step.get("duration", 0.0)
                            ))
                            
                    results.append(RouteResult(
                        provider="ors",
                        distance_m=summary.get("distance", 0.0),
                        duration_s=summary.get("duration", 0.0),
                        geometry_geojson=geometry,
                        steps=steps,
                        raw_metadata=data.get("metadata", {})
                    ))
                return results
            except Exception as e:
                logger.error(f"ORS route error: {e}")
                return []

    async def table(self, locations: List[Coords]) -> TravelTimeMatrix:
        url = f"{self.base_url}/v2/matrix/driving-car"
        payload = {
            "locations": [[loc.lon, loc.lat] for loc in locations],
            "metrics": ["duration", "distance"]
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                return TravelTimeMatrix(
                    provider="ors",
                    durations_s=data.get("durations", []),
                    distances_m=data.get("distances", []),
                    locations=locations
                )
            except Exception as e:
                logger.error(f"ORS table error: {e}")
                return TravelTimeMatrix(provider="ors", durations_s=[], distances_m=[], locations=locations)

    async def nearest(self, point: Coords) -> SnappedPoint:
        return SnappedPoint(
            original=point,
            snapped=point,
            road_name="",
            distance_m=0.0
        )

    async def health_check(self) -> bool:
        url = f"{self.base_url}/v2/health"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=5.0)
                return response.status_code == 200
            except Exception:
                return False
