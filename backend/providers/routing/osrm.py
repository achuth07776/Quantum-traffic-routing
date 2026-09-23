import os
import math
import httpx
import logging
from typing import List, Optional
from .base import BaseRoutingProvider, Coords, RouteResult, RouteStep, TravelTimeMatrix, SnappedPoint

logger = logging.getLogger(__name__)

class OSRMRoutingProvider(BaseRoutingProvider):
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
    
    async def route(self, origin: Coords, destination: Coords, alternatives: bool = False) -> List[RouteResult]:
        alt_param = "3" if alternatives else "false"
        url = f"{self.base_url}/route/v1/driving/{origin.lon},{origin.lat};{destination.lon},{destination.lat}?overview=full&geometries=geojson&steps=true&alternatives={alt_param}"
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for route in data.get("routes", []):
                    geometry = route.get("geometry", {})
                    
                    def _format_step(step_obj):
                        m = step_obj.get("maneuver", {})
                        raw_name = (step_obj.get("name") or "").strip()
                        raw_ref = (step_obj.get("ref") or "").strip()
                        raw_dest = (step_obj.get("destinations") or "").strip()

                        # Priority: road name -> road ref -> destination -> Unnamed road
                        if raw_name:
                            road_name = raw_name
                        elif raw_ref:
                            road_name = raw_ref
                        elif raw_dest:
                            road_name = f"Toward {raw_dest}"
                        else:
                            road_name = "Unnamed road"

                        m_type = (m.get("type") or "").strip().lower()
                        m_mod = (m.get("modifier") or "").strip().lower()

                        if m_type == "depart":
                            instr = f"Depart onto {road_name}"
                        elif m_type == "arrive":
                            instr = "Arrive at destination"
                        elif m_type in ("turn", "end of road", "fork"):
                            instr = f"Turn {m_mod} onto {road_name}" if m_mod else f"Turn onto {road_name}"
                        elif m_type == "continue":
                            instr = f"Make a U-turn onto {road_name}" if m_mod == "uturn" else f"Continue onto {road_name}"
                        elif m_type == "new name":
                            instr = f"Continue onto {road_name}"
                        elif m_type == "roundabout":
                            exit_no = m.get("exit")
                            instr = f"At roundabout, take exit {exit_no} onto {road_name}" if exit_no else f"Enter roundabout onto {road_name}"
                        elif m_type == "on ramp":
                            instr = f"Take ramp onto {road_name}"
                        elif m_type == "off ramp":
                            instr = f"Take exit ramp onto {road_name}"
                        else:
                            cap = m_type.replace("_", " ").capitalize() if m_type else "Proceed"
                            instr = f"{cap} onto {road_name}"

                        return RouteStep(
                            instruction=instr,
                            road_name=road_name,
                            distance_m=step_obj.get("distance", 0.0),
                            duration_s=step_obj.get("duration", 0.0)
                        )

                    steps = []
                    for leg in route.get("legs", []):
                        for step in leg.get("steps", []):
                            steps.append(_format_step(step))
                            
                    results.append(RouteResult(
                        provider="osrm",
                        distance_m=route.get("distance", 0.0),
                        duration_s=route.get("duration", 0.0),
                        geometry_geojson=geometry,
                        steps=steps,
                        raw_metadata={"code": data.get("code")}
                    ))

                return results
            except Exception as e:
                logger.error(f"OSRM route error: {e}")
                return []

    async def table(self, locations: List[Coords]) -> TravelTimeMatrix:
        coords_str = ";".join([f"{loc.lon},{loc.lat}" for loc in locations])
        url = f"{self.base_url}/table/v1/driving/{coords_str}?annotations=duration,distance"
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                durations = data.get("durations", [])
                distances = data.get("distances", [])
                if not durations or not distances or len(durations) != len(locations):
                    raise ValueError("Incomplete table from OSRM")
                
                return TravelTimeMatrix(
                    provider="osrm",
                    durations_s=durations,
                    distances_m=distances,
                    locations=locations
                )
            except Exception as e:
                logger.error(f"OSRM table error: {e}")
                return TravelTimeMatrix(provider="osrm", durations_s=[], distances_m=[], locations=locations)

    async def nearest(self, point: Coords) -> Optional[SnappedPoint]:
        url = (
            f"{self.base_url}/nearest/v1/driving/"
            f"{point.lon},{point.lat}?number=1"
        )
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                waypoints = data.get("waypoints") or []
                if not waypoints:
                    return None
                waypoint = waypoints[0]
                location = waypoint.get("location")
                if not location or len(location) < 2:
                    return None
                road_name = (
                    (waypoint.get("name") or "").strip()
                    or (waypoint.get("ref") or "").strip()
                    or "Unnamed road"
                )
                distance_m = float(waypoint.get("distance", float("nan")))
                if not math.isfinite(distance_m) or distance_m < 0:
                    return None
                return SnappedPoint(
                    original=point,
                    snapped=Coords(
                        lon=float(location[0]),
                        lat=float(location[1]),
                    ),
                    road_name=road_name,
                    distance_m=distance_m,
                )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            logger.warning(
                "OSRM nearest failed for %.6f,%.6f: %s",
                point.lat,
                point.lon,
                type(exc).__name__,
            )
            return None

    async def health_check(self) -> bool:
        url = f"{self.base_url}/route/v1/driving/0,0;0,0"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=5.0)
                return response.status_code in [200, 400]
            except Exception:
                return False
