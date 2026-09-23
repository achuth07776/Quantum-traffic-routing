"""
TomTom Traffic Provider.

Ingests real-time traffic flow via TomTom Traffic Flow Segment API v4
and incident details via TomTom Traffic Incidents API v5.
"""

import os
import math
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional
import httpx
from pydantic import BaseModel

from .base import BaseTrafficProvider, TrafficSnapshot, TrafficObservation, IncidentReport
from .route_traffic_matcher import FlowObservation, match_flow_to_route

logger = logging.getLogger(__name__)


class TomTomFlowSegment(BaseModel):
    current_speed_kmh: float
    free_flow_speed_kmh: float
    current_travel_time_s: float
    free_flow_travel_time_s: float
    confidence: float
    road_closure: bool
    coordinates: List[Tuple[float, float]] = []  # [(lat, lon), ...]


class TomTomTrafficProvider(BaseTrafficProvider):
    """Real-time Traffic Flow and Incidents Provider using TomTom APIs."""

    def __init__(self, api_key: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("TOMTOM_API_KEY", "")
        self.flow_base_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
        self.incidents_base_url = "https://api.tomtom.com/traffic/services/5/incidentDetails"
        # Default Visakhapatnam Metropolitan Bounding Box: (minLon, minLat, maxLon, maxLat)
        self.default_bbox: Tuple[float, float, float, float] = (83.10, 17.60, 83.45, 17.90)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def get_flow_segment(
        self,
        lat: float,
        lon: float,
        timeout: float = 6.0
    ) -> Optional[TomTomFlowSegment]:
        """
        Queries real-time flow speed and travel time for a specific road coordinate.
        """
        if not self.is_configured():
            return None

        url = self.flow_base_url
        params = {
            "point": f"{lat},{lon}",
            "key": self.api_key,
            "unit": "KMPH"
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 401:
                    logger.error("TomTomTrafficProvider: HTTP 401 Unauthorized.")
                    return None
                if resp.status_code == 429:
                    logger.error("TomTomTrafficProvider: HTTP 429 Rate Limit Exceeded.")
                    return None
                resp.raise_for_status()
                data = resp.json()
                fs = data.get("flowSegmentData", {})
                if not fs:
                    return None

                curr_speed = float(fs.get("currentSpeed", 0.0))
                free_speed = float(fs.get("freeFlowSpeed", curr_speed))
                curr_time = float(fs.get("currentTravelTime", 0.0))
                free_time = float(fs.get("freeFlowTravelTime", curr_time))
                conf = float(fs.get("confidence", 1.0))
                closure = bool(fs.get("roadClosure", False))

                coords_list = []
                raw_coords = fs.get("coordinates", {}).get("coordinate", [])
                for pt in raw_coords:
                    coords_list.append((float(pt.get("latitude", 0.0)), float(pt.get("longitude", 0.0))))

                return TomTomFlowSegment(
                    current_speed_kmh=curr_speed,
                    free_flow_speed_kmh=free_speed,
                    current_travel_time_s=curr_time,
                    free_flow_travel_time_s=free_time,
                    confidence=conf,
                    road_closure=closure,
                    coordinates=coords_list
                )
        except Exception as e:
            logger.warning(f"TomTomTrafficProvider: flow segment query failed at ({lat}, {lon}): {type(e).__name__}")
            return None

    async def sample_flow_along_route(
        self,
        coords_lon_lat: List[Tuple[float, float]],
        target_spacing_m: float = 500.0,
        max_samples: int = 40
    ) -> List[FlowObservation]:
        """
        Adaptively samples real-time TomTom flow observations along a route polyline:
        ~500m target spacing, max 40 samples, deduplicated coordinates.
        """
        if not self.is_configured() or not coords_lon_lat or len(coords_lon_lat) < 2:
            return []

        # 1. Cumulative distance along polyline
        cum_dist = [0.0]
        for i in range(len(coords_lon_lat) - 1):
            p1_lon, p1_lat = coords_lon_lat[i]
            p2_lon, p2_lat = coords_lon_lat[i + 1]
            mean_lat = math.radians((p1_lat + p2_lat) / 2.0)
            dx = (p2_lon - p1_lon) * 111139.0 * math.cos(mean_lat)
            dy = (p2_lat - p1_lat) * 111139.0
            cum_dist.append(cum_dist[-1] + math.sqrt(dx * dx + dy * dy))

        total_dist_m = cum_dist[-1]
        sample_points: List[Tuple[float, float]] = []

        if total_dist_m < 10.0:
            sample_points.append((coords_lon_lat[0][1], coords_lon_lat[0][0]))
        else:
            num_samples = min(max_samples, max(2, int(math.ceil(total_dist_m / target_spacing_m))))
            target_distances = [s * (total_dist_m / (num_samples + 1)) for s in range(1, num_samples + 1)]
            for td in target_distances:
                for j in range(len(cum_dist) - 1):
                    if cum_dist[j] <= td <= cum_dist[j + 1]:
                        seg_len = cum_dist[j + 1] - cum_dist[j]
                        t = (td - cum_dist[j]) / seg_len if seg_len > 0 else 0.0
                        lon = coords_lon_lat[j][0] + t * (coords_lon_lat[j + 1][0] - coords_lon_lat[j][0])
                        lat = coords_lon_lat[j][1] + t * (coords_lon_lat[j + 1][1] - coords_lon_lat[j][1])
                        sample_points.append((lat, lon))
                        break

        # Deduplicate points closer than 50m
        deduped: List[Tuple[float, float]] = []
        for lat, lon in sample_points:
            if not any(abs(lat - dlat) < 0.00045 and abs(lon - dlon) < 0.00045 for dlat, dlon in deduped):
                deduped.append((lat, lon))

        # Query TomTom flow segment concurrently
        tasks = [self.get_flow_segment(lat, lon) for lat, lon in deduped]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        observations: List[FlowObservation] = []
        for (lat, lon), res in zip(deduped, results):
            if isinstance(res, TomTomFlowSegment) and res is not None:
                observations.append(
                    FlowObservation(
                        current_speed_kmh=res.current_speed_kmh,
                        free_flow_speed_kmh=res.free_flow_speed_kmh,
                        confidence=res.confidence,
                        road_closure=res.road_closure,
                        coordinates_latlon=res.coordinates if res.coordinates else [(lat, lon)]
                    )
                )

        return observations

    async def evaluate_route(
        self,
        geometry_geojson: Dict[str, Any],
        base_duration_s: float,
        incidents: Optional[List[IncidentReport]] = None,
        max_samples: int = 40
    ) -> Dict[str, Any]:
        """
        Evaluates real-time traffic along a route using true Shapely LineString geometry matching.
        """
        coords_lon_lat = geometry_geojson.get("coordinates", []) if isinstance(geometry_geojson, dict) else []
        if not coords_lon_lat or len(coords_lon_lat) < 2:
            return {
                "provider": "TomTom",
                "state": "UNAVAILABLE",
                "observations_used": 0,
                "coverage_pct": 0.0,
                "traffic_coverage_pct": 0.0,
                "matched_length_m": 0.0,
                "route_length_m": 0.0,
                "matched_segments": 0,
                "unmatched_segments": 0,
                "traffic_duration_s": base_duration_s,
                "traffic_delay_s": 0.0,
                "avg_current_speed_kmh": 0.0,
                "avg_free_flow_speed_kmh": 0.0,
                "confidence": 0.0,
                "incidents_count": 0,
                "is_blocked": False,
                "block_reason": None,
            }

        flow_obs = await self.sample_flow_along_route(coords_lon_lat, max_samples=max_samples)
        return match_flow_to_route(
            coords_lon_lat=coords_lon_lat,
            base_duration_s=base_duration_s,
            flow_observations=flow_obs,
            tolerance_m=60.0,
            incidents=incidents
        )

    async def match_traffic_to_route_segments(
        self,
        coords_lon_lat: List[Tuple[float, float]],
        base_duration_s: float,
        incidents: Optional[List[IncidentReport]] = None,
        max_samples: int = 40
    ) -> Dict[str, Any]:
        """
        Compatibility adapter delegating to evaluate_route.
        """
        return await self.evaluate_route(
            geometry_geojson={"coordinates": coords_lon_lat},
            base_duration_s=base_duration_s,
            incidents=incidents,
            max_samples=max_samples
        )

    async def get_incidents(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        timeout: float = 6.0
    ) -> List[IncidentReport]:
        """
        Retrieves real-time traffic incidents (closures, delays, roadworks) within the bounding box.
        """
        if not self.is_configured():
            return []

        if not bbox:
            bbox = self.default_bbox

        minLon, minLat, maxLon, maxLat = bbox
        url = self.incidents_base_url
        params = {
            "bbox": f"{minLon},{minLat},{maxLon},{maxLat}",
            "key": self.api_key,
            "fields": "{incidents{type,geometry{type,coordinates},properties{iconCategory,magnitudeOfDelay,delay,length,events{description,code},startTime,endTime}}}"
        }

        incidents: List[IncidentReport] = []
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return []
                data = resp.json()

                raw_incidents = data.get("incidents", [])
                for idx, item in enumerate(raw_incidents):
                    props = item.get("properties", {})
                    geom = item.get("geometry", {})
                    events = props.get("events", [])
                    desc_parts = [e.get("description", "") for e in events if e.get("description")]
                    description = "; ".join(desc_parts) if desc_parts else "Traffic incident / restriction"

                    # Map iconCategory to standardized severity / type
                    # 8: Road Closed, 6: Congestion, 1: Accident
                    icon_cat = props.get("iconCategory", 0)
                    inc_type = "ROAD_CLOSURE" if icon_cat == 8 or any("closed" in d.lower() for d in desc_parts) else "CONGESTION"
                    severity = "CRITICAL" if inc_type == "ROAD_CLOSURE" else "MEDIUM"

                    delay_val = float(props.get("delay", 0.0) or 0.0)
                    mag = props.get("magnitudeOfDelay", 0)
                    if delay_val <= 0.0:
                        if mag == 1:
                            delay_val = 120.0
                        elif mag == 2:
                            delay_val = 300.0
                        elif mag == 3:
                            delay_val = 600.0

                    length_val = float(props.get("length", 0.0) or 0.0)

                    coords = geom.get("coordinates", [])
                    lat, lon = 0.0, 0.0
                    if coords:
                        if geom.get("type") == "Point" and len(coords) >= 2:
                            lon, lat = float(coords[0]), float(coords[1])
                        elif geom.get("type") == "LineString" and len(coords) > 0 and len(coords[0]) >= 2:
                            lon, lat = float(coords[0][0]), float(coords[0][1])

                    incidents.append(
                        IncidentReport(
                            incident_id=f"tt_inc_{idx}_{props.get('startTime', '')}",
                            type=inc_type,
                            severity=severity,
                            lat=lat,
                            lon=lon,
                            description=description,
                            start_time=props.get("startTime", datetime.now(timezone.utc).isoformat()),
                            expected_end_time=props.get("endTime"),
                            source="TomTom",
                            delay_seconds=delay_val,
                            length_meters=length_val
                        )
                    )
        except Exception as e:
            logger.warning(f"TomTomTrafficProvider: incidents query failed: {type(e).__name__}")
            return []

        return incidents

    async def get_flow(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> TrafficSnapshot:
        """
        Samples real-time traffic flow across key arterial checkpoint nodes in Visakhapatnam.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        if not self.is_configured():
            return TrafficSnapshot(
                provider="TomTom",
                observed_at=now_str,
                segments_updated=0,
                observations=[],
                incidents=[],
                source_status="UNAVAILABLE",
                traffic_source_type="UNAVAILABLE"
            )

        # Strategic arterial checkpoints across Greater Visakhapatnam:
        # Beach Rd North, Beach Rd South, NH16 Maddilapalem, NH16 NAD, Asilmetta, Gajuwaka, Rushikonda
        checkpoints = [
            ("beach_road_north", 17.7441, 83.3412, "Dr NTR Beach Road (North)"),
            ("beach_road_south", 17.7144, 83.3341, "Dr NTR Beach Road (South)"),
            ("nh16_maddilapalem", 17.7348, 83.3245, "NH16 Maddilapalem Junction"),
            ("nh16_nad", 17.7482, 83.2189, "NAD Junction Flyover Arterial"),
            ("asilmetta", 17.7195, 83.3105, "Asilmetta / Siripuram Arterial"),
            ("rushikonda_link", 17.7818, 83.3854, "Rushikonda Beach Road Corridor"),
            ("gajuwaka_corridor", 17.6896, 83.2128, "Gajuwaka Industrial Corridor")
        ]

        observations: List[TrafficObservation] = []
        for cid, lat, lon, name in checkpoints:
            fs = await self.get_flow_segment(lat, lon)
            if fs:
                # Jam factor approximation: 0 to 10 scale based on speed ratio
                ratio = fs.current_speed_kmh / max(fs.free_flow_speed_kmh, 5.0)
                jam_factor = round(max(0.0, min(10.0, (1.0 - ratio) * 10.0)), 1)
                observations.append(
                    TrafficObservation(
                        segment_id=name,
                        speed_kmh=fs.current_speed_kmh,
                        free_flow_speed_kmh=fs.free_flow_speed_kmh,
                        jam_factor=jam_factor,
                        confidence=fs.confidence,
                        observed_at=now_str,
                        source="TomTom"
                    )
                )

        incidents = await self.get_incidents(bbox)

        status = "LIVE" if len(observations) > 0 else "UNAVAILABLE"
        source_type = "LIVE_PROVIDER" if len(observations) > 0 else "UNAVAILABLE"

        return TrafficSnapshot(
            provider="TomTom",
            observed_at=now_str,
            segments_updated=len(observations),
            observations=observations,
            incidents=incidents,
            source_status=status,
            raw_observations_count=len(observations),
            mapped_segments_count=len(observations),
            traffic_source_type=source_type
        )

    async def health_check(self) -> bool:
        if not self.is_configured():
            return False
        # Lightweight check: RK Beach point flow query
        fs = await self.get_flow_segment(17.7144, 83.3341, timeout=4.0)
        return fs is not None