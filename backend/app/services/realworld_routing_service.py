"""
Real-World Routing Service for Visakhapatnam Traffic Platform.

Delegates road-valid route generation to Open Source Routing Machine (OSRM)
and fuses real-time traffic flow and incident observations from TomTom.
"""
import os
import time
import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.domain.place import PlaceResolution
from app.services.place_resolution_service import PlaceResolutionService
from providers.routing.base import BaseRoutingProvider, Coords
from providers.routing.ors import ORSRoutingProvider
from providers.routing.osrm import OSRMRoutingProvider
from providers.traffic.tomtom import TomTomTrafficProvider
from providers.search.tomtom import TomTomSearchProvider
from transport.landmarks import LandmarkRegistry
from transport.provenance import DataProvenanceTracker
from transport.canonical_roads import CanonicalRoadRegistry, DataFusionEngine

logger = logging.getLogger(__name__)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodetic distance in meters between two lat/lon coordinates."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class RealWorldRoutingService:
    """
    Orchestrates real-world routing using OSRM routing engine fused with TomTom traffic observations.

    Architecture:
        Coordinates -> Snap to Network -> OSRM Routing Engine -> Candidate Routes -> TomTom Traffic Fusion -> Result

    The routing engine handles road-valid path generation.
    QPSO is NOT used for basic A-to-B routing - it belongs in fleet/VRP optimization.
    """

    def __init__(
        self,
        landmark_registry: Optional[LandmarkRegistry] = None,
        routing_provider: Optional[BaseRoutingProvider] = None,
        traffic_provider: Optional[TomTomTrafficProvider] = None,
        search_provider: Optional[TomTomSearchProvider] = None
    ):
        self.landmarks = landmark_registry or LandmarkRegistry()
        self.canonical_roads = CanonicalRoadRegistry()
        self.data_fusion = DataFusionEngine(self.canonical_roads)
        self.traffic_provider = traffic_provider or TomTomTrafficProvider()
        self.search_provider = search_provider or TomTomSearchProvider()
        self.provenance = DataProvenanceTracker()
        if routing_provider is not None:
            self._provider = routing_provider
            self._provider_name = getattr(routing_provider, "name", "OSRM")
        else:
            self._provider = None
            self._provider_name = "NONE"
            self._initialize_provider()
        self.place_resolver = PlaceResolutionService(
            routing_provider=self._provider,
            search_provider=self.search_provider
        )

    def _initialize_provider(self):
        """Initialize the best available routing provider (Default: OSRM)."""
        osrm_url = os.environ.get("OSRM_BASE_URL", "")
        ors_key = os.environ.get("ORS_API_KEY", "")

        if osrm_url:
            self._provider = OSRMRoutingProvider(base_url=osrm_url)
            self._provider_name = "OSRM"
        elif ors_key:
            self._provider = ORSRoutingProvider(api_key=ors_key)
            self._provider_name = "ORS"
        else:
            self._provider = OSRMRoutingProvider(
                base_url="https://router.project-osrm.org"
            )
            self._provider_name = "OSRM_PUBLIC"

        self.provenance.update_routing_provider(self._provider_name)
        self.provenance.update_network_source("OpenStreetMap")
        self.place_resolver = PlaceResolutionService(
            routing_provider=self._provider,
            search_provider=self.search_provider
        )

    async def route_by_landmarks(
        self,
        origin_id: str,
        destination_id: str,
        alternatives: bool = False,
        simulated_multiplier: float = 1.0,
        simulated_closed: bool = False,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Route between two landmarks by their registry IDs.
        Returns real road geometry, base routing duration, and traffic-aware travel time.
        """
        origin_lm = self.landmarks.get_by_id(origin_id)
        dest_lm = self.landmarks.get_by_id(destination_id)

        if not origin_lm:
            raise ValueError(f"Unknown origin landmark: '{origin_id}'")
        if not dest_lm:
            raise ValueError(f"Unknown destination landmark: '{destination_id}'")

        effective_multiplier = simulated_multiplier
        beach_north = self.canonical_roads.get_by_id("cr_beach_road_north")
        beach_south = self.canonical_roads.get_by_id("cr_beach_road_south")
        corridor_closed = bool(
            (beach_north and not beach_north.is_available) or (beach_south and not beach_south.is_available)
        )
        is_closed_override = simulated_closed or corridor_closed

        if corridor_closed:
            effective_multiplier = max(effective_multiplier, 3.0)
        elif (beach_north and beach_north.speed_ratio < 0.5) or (beach_south and beach_south.speed_ratio < 0.5):
            effective_multiplier = max(effective_multiplier, 3.0)

        # Resolve canonical place objects for origin and destination
        origin_res = await self.place_resolver.resolve_place(
            name=origin_lm.name,
            lat=origin_lm.lat,
            lon=origin_lm.lon,
            category=origin_lm.category,
            entry_points=getattr(origin_lm, "entry_points", None)
        )
        dest_res = await self.place_resolver.resolve_place(
            name=dest_lm.name,
            lat=dest_lm.lat,
            lon=dest_lm.lon,
            category=dest_lm.category,
            entry_points=getattr(dest_lm, "entry_points", None)
        )

        return await self.route_by_coords(
            origin_lat=origin_res.latitude,
            origin_lon=origin_res.longitude,
            dest_lat=dest_res.latitude,
            dest_lon=dest_res.longitude,
            origin_name=origin_res.name,
            dest_name=dest_res.name,
            alternatives=alternatives,
            simulated_multiplier=effective_multiplier,
            simulated_closed=is_closed_override,
            origin_resolution=origin_res,
            dest_resolution=dest_res
        )

    async def route_by_coords(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        origin_name: str = "",
        dest_name: str = "",
        alternatives: bool = False,
        simulated_multiplier: float = 1.0,
        simulated_closed: bool = False,
        origin_place: Optional[Dict[str, Any]] = None,
        dest_place: Optional[Dict[str, Any]] = None,
        origin_resolution: Optional[PlaceResolution] = None,
        dest_resolution: Optional[PlaceResolution] = None
    ) -> Dict[str, Any]:
        """
        Route between two locations using canonical PlaceResolution access points,
        OSRM road network routing, and segment-level TomTom traffic matching.
        """
        start_time = time.time()

        # 1. Canonical Place Resolution for Origin
        if origin_resolution is None:
            if origin_place:
                origin_resolution = await self.place_resolver.resolve_place(
                    name=origin_place.get("name") or origin_name or "Origin",
                    lat=float(origin_place.get("latitude", origin_lat)),
                    lon=float(origin_place.get("longitude", origin_lon)),
                    address=origin_place.get("address", ""),
                    category=origin_place.get("category", "place"),
                    provider_place_id=str(origin_place.get("provider_place_id") or origin_place.get("id", "")),
                    entry_points=origin_place.get("entry_points")
                )
            else:
                origin_resolution = await self.place_resolver.resolve_place(
                    name=origin_name or "Origin",
                    lat=origin_lat,
                    lon=origin_lon
                )

        # 2. Canonical Place Resolution for Destination
        if dest_resolution is None:
            if dest_place:
                dest_resolution = await self.place_resolver.resolve_place(
                    name=dest_place.get("name") or dest_name or "Destination",
                    lat=float(dest_place.get("latitude", dest_lat)),
                    lon=float(dest_place.get("longitude", dest_lon)),
                    address=dest_place.get("address", ""),
                    category=dest_place.get("category", "place"),
                    provider_place_id=str(dest_place.get("provider_place_id") or dest_place.get("id", "")),
                    entry_points=dest_place.get("entry_points")
                )
            else:
                dest_resolution = await self.place_resolver.resolve_place(
                    name=dest_name or "Destination",
                    lat=dest_lat,
                    lon=dest_lon
                )

        # 3. Route between validated drivable access coordinates
        origin_coords = Coords(lat=origin_resolution.access_latitude, lon=origin_resolution.access_longitude)
        dest_coords = Coords(lat=dest_resolution.access_latitude, lon=dest_resolution.access_longitude)

        try:
            routes = await self._provider.route(origin_coords, dest_coords, alternatives=alternatives)
        except Exception as e:
            return {
                "status": "ERROR",
                "error": f"Routing provider ({self._provider_name}) failed: {str(e)}",
                "provider": self._provider_name,
                "origin_resolution": origin_resolution.model_dump(),
                "destination_resolution": dest_resolution.model_dump(),
                "provenance": self.provenance.get_metadata()
            }

        if not routes:
            return {
                "status": "NO_ROUTE",
                "message": "No feasible route found between the given locations.",
                "provider": self._provider_name,
                "origin": origin_resolution.model_dump(),
                "destination": dest_resolution.model_dump(),
                "origin_resolution": origin_resolution.model_dump(),
                "destination_resolution": dest_resolution.model_dump(),
                "provenance": self.provenance.get_metadata()
            }

        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        # Log the 13 required instrumentation metrics (Directive 6)
        p_route = routes[0]
        p_geom_coords = p_route.geometry_geojson.get("coordinates", [])
        geom_length_m = 0.0
        for i in range(len(p_geom_coords) - 1):
            geom_length_m += haversine_m(p_geom_coords[i][1], p_geom_coords[i][0], p_geom_coords[i+1][1], p_geom_coords[i+1][0])

        logger.info(
            f"[ROUTING_TRACE_13_METRICS] "
            f"1.TomTomOrigLat={origin_resolution.latitude} "
            f"2.TomTomOrigLon={origin_resolution.longitude} "
            f"3.TomTomDestLat={dest_resolution.latitude} "
            f"4.TomTomDestLon={dest_resolution.longitude} "
            f"5.OSRMOrigSnapLat={origin_resolution.access_latitude} "
            f"6.OSRMOrigSnapLon={origin_resolution.access_longitude} "
            f"7.OSRMDestSnapLat={dest_resolution.access_latitude} "
            f"8.OSRMDestSnapLon={dest_resolution.access_longitude} "
            f"9.OrigSnapDistM={origin_resolution.snap_distance_m} "
            f"10.DestSnapDistM={dest_resolution.snap_distance_m} "
            f"11.OSRMRouteDistM={p_route.distance_m} "
            f"12.OSRMRouteDurS={p_route.duration_s} "
            f"13.RouteGeomLenM={round(geom_length_m, 1)}"
        )

        # Defensible Spatial Traffic Matching with TomTom
        # Fetch incidents in route bounding box
        min_lat = min(origin_lat, dest_lat) - 0.02
        max_lat = max(origin_lat, dest_lat) + 0.02
        min_lon = min(origin_lon, dest_lon) - 0.02
        max_lon = max(origin_lon, dest_lon) + 0.02
        route_bbox = (min_lon, min_lat, max_lon, max_lat)

        # Check if data fusion has an ingested snapshot with incidents (e.g. from controlled simulation/test)
        if self.data_fusion._last_snapshot and self.data_fusion._last_snapshot.incidents is not None:
            incidents = self.data_fusion._last_snapshot.incidents
        else:
            incidents = await self.traffic_provider.get_incidents(route_bbox)

        evaluated_candidates = []
        for idx, cand_route in enumerate(routes):
            cand_route.geometry_geojson.get("coordinates", [])
            base_dur_s = round(cand_route.duration_s, 1)
            base_dist_m = round(cand_route.distance_m, 1)

            # Numerical guards: reject negative, NaN, Inf, or zero duration on nonzero distance (Item 9)
            if (base_dist_m < 0 or base_dur_s < 0 or
                math.isnan(base_dist_m) or math.isnan(base_dur_s) or
                math.isinf(base_dist_m) or math.isinf(base_dur_s) or
                (base_dist_m > 0 and base_dur_s <= 0)):
                raise ValueError(f"Invalid route numerical values: distance={base_dist_m}, duration={base_dur_s}")

            # 1. True Segment-Level TomTom Traffic Matching via Shapely
            traffic_match = await self.traffic_provider.evaluate_route(
                geometry_geojson=cand_route.geometry_geojson,
                base_duration_s=base_dur_s,
                incidents=incidents
            )

            # Defensively extract traffic matching attributes (resilient against mocks)
            if not isinstance(traffic_match, dict):
                traffic_match = {}

            is_blocked = bool(traffic_match.get("is_blocked", False)) if isinstance(traffic_match.get("is_blocked"), bool) else False
            block_reason = traffic_match.get("block_reason") if isinstance(traffic_match.get("block_reason"), str) else None

            # Simulation overrides (only for explicit controlled research/test requests)
            if simulated_closed:
                if idx == 0:
                    is_blocked = True
                    block_reason = "Controlled Simulation Road Closure"
                else:
                    # In simulated closure testing, alternatives serve as the bypass corridor
                    is_blocked = False
                    block_reason = None

            raw_matched_len = traffic_match.get("matched_length_m", 0.0)
            matched_len_m = float(raw_matched_len) if isinstance(raw_matched_len, (int, float)) else 0.0

            raw_cov = traffic_match.get("coverage_pct", 0.0)
            coverage_pct = float(raw_cov) if isinstance(raw_cov, (int, float)) else 0.0

            raw_obs_used = traffic_match.get("observations_used", 0)
            obs_used = int(raw_obs_used) if isinstance(raw_obs_used, (int, float)) else 0

            raw_matched_segs = traffic_match.get("matched_segments", 0)
            matched_segs = int(raw_matched_segs) if isinstance(raw_matched_segs, (int, float)) else 0

            raw_unmatched_segs = traffic_match.get("unmatched_segments", 0)
            unmatched_segs = int(raw_unmatched_segs) if isinstance(raw_unmatched_segs, (int, float)) else 0

            raw_route_len = traffic_match.get("route_length_m", base_dist_m)
            route_len_m = float(raw_route_len) if isinstance(raw_route_len, (int, float)) else base_dist_m

            raw_avg_curr = traffic_match.get("avg_current_speed_kmh", 0.0)
            avg_curr_spd = float(raw_avg_curr) if isinstance(raw_avg_curr, (int, float)) else 0.0

            raw_avg_free = traffic_match.get("avg_free_flow_speed_kmh", 0.0)
            avg_free_spd = float(raw_avg_free) if isinstance(raw_avg_free, (int, float)) else 0.0

            raw_inc_cnt = traffic_match.get("incidents_count", 0)
            inc_cnt = int(raw_inc_cnt) if isinstance(raw_inc_cnt, (int, float)) else 0

            raw_match_state = traffic_match.get("state", "UNAVAILABLE")
            match_state = str(raw_match_state) if isinstance(raw_match_state, str) else "UNAVAILABLE"

            raw_traf_dur = traffic_match.get("traffic_duration_s", base_dur_s)
            traf_dur = float(raw_traf_dur) if isinstance(raw_traf_dur, (int, float)) else base_dur_s

            raw_traf_delay = traffic_match.get("traffic_delay_s", 0.0)
            traf_delay = float(raw_traf_delay) if isinstance(raw_traf_delay, (int, float)) else 0.0

            raw_conf = traffic_match.get("confidence", 0.0)
            conf_val = float(raw_conf) if isinstance(raw_conf, (int, float)) else 0.0

            if is_blocked:
                traffic_dur_s = round(base_dur_s + 1800.0, 1)
                traffic_delay_s = 1800.0
                traffic_source = block_reason or "INCIDENT_CLOSURE"
                traffic_state = "BLOCKED"
                confidence = 0.95
                coverage_pct = coverage_pct
            elif (simulated_multiplier > 1.0) and idx == 0:
                traffic_delay_s = round(base_dur_s * (simulated_multiplier - 1.0), 1)
                traffic_dur_s = round(base_dur_s + traffic_delay_s, 1)
                traffic_source = f"CONTROLLED SIMULATION · {simulated_multiplier:.1f}x TRAVEL-TIME MULTIPLIER"
                traffic_state = "DEMO"
                confidence = 0.95
                coverage_pct = 100.0
            elif match_state in ["LIVE", "PARTIAL"]:
                traffic_dur_s = traf_dur
                traffic_delay_s = traf_delay
                traffic_state = match_state
                confidence = conf_val
                traffic_source = f"TomTom ({traffic_state} · {obs_used} obs, {coverage_pct}% coverage)"
            else:
                traffic_dur_s = base_dur_s
                traffic_delay_s = 0.0
                traffic_source = "TRAFFIC UNAVAILABLE · BASE OSRM TIME"
                traffic_state = "UNAVAILABLE"
                confidence = 0.0
                coverage_pct = 0.0

            # 2. Step-Sum Conservation Invariant Check
            sum_step_dist = sum(s.distance_m for s in cand_route.steps) if cand_route.steps else base_dist_m
            sum_step_dur = sum(s.duration_s for s in cand_route.steps) if cand_route.steps else base_dur_s
            step_dist_diff = round(abs(sum_step_dist - base_dist_m), 2)
            step_dur_diff = round(abs(sum_step_dur - base_dur_s), 2)
            is_step_conserved = (step_dist_diff <= 0.5 and step_dur_diff <= 0.5)

            # 3. Speed Sanity Validation (v_avg = (D / T) * 3.6 km/h)
            v_avg_kmh = round((base_dist_m / max(1.0, traffic_dur_s)) * 3.6, 1)
            if 5.0 <= v_avg_kmh <= 110.0:
                speed_sanity = {
                    "status": "VALID",
                    "avg_speed_kmh": v_avg_kmh,
                    "reason": "Average speed within realistic urban/arterial limits (5.0 - 110.0 km/h)."
                }
            else:
                speed_sanity = {
                    "status": "SUSPICIOUS",
                    "avg_speed_kmh": v_avg_kmh,
                    "reason": f"Average speed {v_avg_kmh} km/h is outside expected urban transit bounds (5.0 - 110.0 km/h)."
                }

            # Traffic metadata
            traffic_meta = {
                "provider": "TomTom",
                "state": traffic_state,
                "observations_used": obs_used,
                "coverage_pct": coverage_pct,
                "traffic_coverage_pct": coverage_pct,
                "matched_length_m": matched_len_m,
                "matched_length_km": round(matched_len_m / 1000.0, 2),
                "route_length_m": route_len_m,
                "route_length_km": round(base_dist_m / 1000.0, 2),
                "matched_segments": matched_segs,
                "unmatched_segments": unmatched_segs,
                "traffic_delay_s": traffic_delay_s
            }

            evaluated_candidates.append({
                "route": cand_route,
                "original_index": idx,
                "base_duration_s": base_dur_s,
                "base_duration_min": round(base_dur_s / 60.0, 1),
                "traffic_duration_s": traffic_dur_s,
                "traffic_duration_min": round(traffic_dur_s / 60.0, 1) if traffic_dur_s >= 0 else -1.0,
                "traffic_delay_s": traffic_delay_s,
                "traffic_delay_min": round(traffic_delay_s / 60.0, 1),
                "traffic_source": traffic_source,
                "traffic_freshness": traffic_state,
                "confidence": confidence,
                "coverage_pct": coverage_pct,
                "avg_current_speed_kmh": avg_curr_spd or v_avg_kmh,
                "avg_free_flow_speed_kmh": avg_free_spd or v_avg_kmh,
                "matched_incidents_count": inc_cnt,
                "is_blocked": is_blocked,
                "block_reason": block_reason,
                "step_conservation": {
                    "step_dist_diff_m": step_dist_diff,
                    "step_dur_diff_s": step_dur_diff,
                    "is_conserved": is_step_conserved,
                    "status": "PASSED" if is_step_conserved else "VIOLATED",
                    "dist_diff_m": step_dist_diff,
                    "dur_diff_s": step_dur_diff
                },
                "speed_sanity": speed_sanity,
                "traffic": traffic_meta
            })

        # Exclude blocked candidates from selection
        open_candidates = [c for c in evaluated_candidates if not c["is_blocked"]]
        primary_cand = evaluated_candidates[0]

        rerouted = False
        reroute_reason = None
        time_saved_min = 0.0
        old_duration_min = None
        new_duration_min = None

        if not open_candidates:
            # If all candidates are blocked, select primary candidate with clear caution advisory
            best_cand = primary_cand
            rerouted = True
            reroute_reason = f"All available routes restricted: {best_cand.get('block_reason') or 'Corridor closures'}. Proceed with extreme caution."
        elif primary_cand["is_blocked"]:
            # Primary corridor is blocked: select the fastest open alternative
            best_cand = min(open_candidates, key=lambda c: (c["traffic_duration_s"], c["route"].distance_m))
            rerouted = True
            new_duration_min = round(best_cand["traffic_duration_s"] / 60.0, 1)
            reroute_reason = f"Dynamic Rerouting: Primary corridor is closed ({primary_cand.get('block_reason') or 'Corridor Closure'}). Diverted to open bypass."
        else:
            # Under live traffic: check if an alternative is genuinely faster
            traffic_advantaged_alts = [
                c for c in open_candidates
                if c["original_index"] != 0 and c["traffic_duration_s"] < primary_cand["traffic_duration_s"]
            ]
            if traffic_advantaged_alts and (primary_cand["traffic_delay_s"] > 0 or any(c["traffic_delay_s"] > 0 for c in traffic_advantaged_alts)):
                best_cand = min(traffic_advantaged_alts, key=lambda c: (c["traffic_duration_s"], c["route"].distance_m))
                rerouted = True
                old_duration_min = round(primary_cand["traffic_duration_s"] / 60.0, 1)
                new_duration_min = round(best_cand["traffic_duration_s"] / 60.0, 1)
                time_saved_min = round(old_duration_min - new_duration_min, 1)
                dist_diff_km = round((best_cand['route'].distance_m - primary_cand['route'].distance_m) / 1000.0, 1)
                reroute_reason = (
                    f"Traffic-aware rerouting: Selected alternative is {time_saved_min} min faster "
                    f"(saves {time_saved_min} min; distance delta: {dist_diff_km:+} km) under current TomTom traffic flow."
                )
            else:
                best_cand = primary_cand
                rerouted = False
                if best_cand["traffic_delay_s"] > 0:
                    b_min = best_cand["base_duration_min"]
                    d_min = best_cand["traffic_delay_min"]
                    t_min = best_cand["traffic_duration_min"]
                    cov = best_cand["traffic"]["traffic_coverage_pct"]
                    reroute_reason = f"Traffic-adjusted fastest route. Base routing: {b_min} min | Traffic delay: +{d_min} min | Traffic-adjusted ETA: {t_min} min ({cov}% coverage via TomTom Flow)."
                elif best_cand["traffic_source"] == "TRAFFIC UNAVAILABLE · BASE OSRM TIME" or best_cand.get("coverage_pct", 0) == 0.0:
                    reroute_reason = "Live traffic coverage unavailable for this route corridor. Showing OSRM base routing duration."
                else:
                    b_min = best_cand["base_duration_min"]
                    d_km = round(best_cand["route"].distance_m / 1000.0, 2)
                    reroute_reason = f"Fastest route under normal free-flow conditions ({b_min} min, {d_km} km). Traffic is clear across observed segments."

        # Fact-based "Why this route?" breakdown (Item 20)
        b_min = best_cand["base_duration_min"]
        d_min = best_cand["traffic_delay_min"]
        t_min = best_cand["traffic_duration_min"]
        cov = best_cand["traffic"]["traffic_coverage_pct"]
        if best_cand["traffic"]["state"] == "UNAVAILABLE":
            why_this_route = "Live traffic unavailable for this route. Showing OSRM base routing duration."
        elif d_min > 0:
            why_this_route = f"Base duration: {b_min} min | Traffic delay: +{d_min} min | Traffic-adjusted ETA: {t_min} min ({cov}% coverage via TomTom Flow)"
        else:
            why_this_route = f"Base duration: {b_min} min | Free-flow traffic | Traffic-adjusted ETA: {t_min} min"

        active_route = best_cand["route"]

        is_review_needed = (
            origin_resolution.confidence in ("REVIEW", "INVALID") or
            dest_resolution.confidence in ("REVIEW", "INVALID")
        )
        location_advisory = (
            "Location requires road-access confirmation."
            if is_review_needed
            else None
        )

        result = {
            "status": "SUCCESS",
            "provider": self._provider_name,
            "origin": {
                "name": origin_resolution.name,
                "address": origin_resolution.address,
                "lat": origin_resolution.latitude,
                "lon": origin_resolution.longitude,
                "access_lat": origin_resolution.access_latitude,
                "access_lon": origin_resolution.access_longitude,
                "access_road_name": origin_resolution.access_road_name,
                "snap_distance_m": origin_resolution.snap_distance_m,
                "confidence": origin_resolution.confidence,
                "resolution_method": origin_resolution.resolution_method
            },
            "destination": {
                "name": dest_resolution.name,
                "address": dest_resolution.address,
                "lat": dest_resolution.latitude,
                "lon": dest_resolution.longitude,
                "access_lat": dest_resolution.access_latitude,
                "access_lon": dest_resolution.access_longitude,
                "access_road_name": dest_resolution.access_road_name,
                "snap_distance_m": dest_resolution.snap_distance_m,
                "confidence": dest_resolution.confidence,
                "resolution_method": dest_resolution.resolution_method
            },
            "origin_resolution": origin_resolution.model_dump(),
            "destination_resolution": dest_resolution.model_dump(),
            "location_advisory": location_advisory,
            "why_this_route": why_this_route,
            "traffic": best_cand["traffic"],
            "speed_sanity": best_cand["speed_sanity"],
            "step_conservation": best_cand["step_conservation"],
            "traffic_rerouting": {
                "is_rerouted": rerouted,
                "reroute_reason": reroute_reason,
                "old_duration_min": old_duration_min,
                "new_duration_min": new_duration_min,
                "time_saved_min": time_saved_min if rerouted else 0.0,
                "recommended_route_index": best_cand["original_index"]
            },
            "primary_route": {
                "distance_m": round(active_route.distance_m, 1),
                "distance_km": round(active_route.distance_m / 1000.0, 2),
                "free_flow_duration_s": best_cand["base_duration_s"],
                "free_flow_duration_min": best_cand["base_duration_min"],
                "traffic_duration_s": best_cand["traffic_duration_s"],
                "traffic_duration_min": best_cand["traffic_duration_min"],
                "traffic_delay_s": best_cand["traffic_delay_s"],
                "traffic_delay_min": best_cand["traffic_delay_min"],
                "traffic_source": best_cand["traffic_source"],
                "traffic_freshness": best_cand["traffic_freshness"],
                "coverage_pct": best_cand.get("coverage_pct", 100.0),
                "avg_current_speed_kmh": best_cand.get("avg_current_speed_kmh", 0.0),
                "avg_free_flow_speed_kmh": best_cand.get("avg_free_flow_speed_kmh", 0.0),
                "duration_s": best_cand["traffic_duration_s"] if best_cand["traffic_duration_s"] > 0 else best_cand["base_duration_s"],
                "duration_min": best_cand["traffic_duration_min"] if best_cand["traffic_duration_min"] > 0 else best_cand["base_duration_min"],
                "geometry_geojson": active_route.geometry_geojson,
                "steps": [s.model_dump() for s in active_route.steps],
                "provider": active_route.provider
            },
            "traffic_provenance": {
                "provider": "TomTom",
                "observation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "route_coverage_pct": best_cand.get("coverage_pct", 0.0),
                "traffic_coverage_pct": best_cand.get("coverage_pct", 0.0),
                "matched_observations_count": best_cand["traffic"].get("observations_used", 0),
                "avg_current_speed_kmh": best_cand.get("avg_current_speed_kmh", 0.0),
                "avg_free_flow_speed_kmh": best_cand.get("avg_free_flow_speed_kmh", 0.0),
                "estimated_traffic_delay_min": best_cand["traffic_delay_min"],
                "incidents_on_route_count": best_cand.get("matched_incidents_count", 0),
                "status": best_cand["traffic_freshness"]
            },
            "alternative_routes": [],
            "computation_ms": elapsed_ms,
            "provenance": {
                "routing_engine": self._provider_name,
                "routing_profile": "car",
                "road_network": "OpenStreetMap",
                "traffic_source": best_cand["traffic_source"],
                "traffic_freshness": best_cand["traffic_freshness"],
                "traffic_confidence": best_cand["confidence"],
                "route_coverage_pct": best_cand.get("coverage_pct", 0.0),
                "traffic_coverage_pct": best_cand.get("coverage_pct", 0.0),
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }

        for cand in evaluated_candidates:
            if cand["original_index"] == best_cand["original_index"]:
                continue
            r = cand["route"]
            result["alternative_routes"].append({
                "index": cand["original_index"],
                "distance_m": round(r.distance_m, 1),
                "distance_km": round(r.distance_m / 1000.0, 2),
                "free_flow_duration_min": cand["base_duration_min"],
                "traffic_duration_min": cand["traffic_duration_min"],
                "traffic_delay_min": cand["traffic_delay_min"],
                "duration_s": cand["traffic_duration_s"] if cand["traffic_duration_s"] > 0 else cand["base_duration_s"],
                "duration_min": cand["traffic_duration_min"] if cand["traffic_duration_min"] > 0 else cand["base_duration_min"],
                "is_blocked": cand["is_blocked"],
                "speed_sanity": cand["speed_sanity"],
                "geometry_geojson": r.geometry_geojson,
                "provider": r.provider
            })

        return result

    async def travel_time_matrix(
        self,
        landmark_ids: Optional[List[str]] = None,
        locations: Optional[List[Coords]] = None,
        location_names: Optional[List[str]] = None,
        simulated_incident_multiplier: float = 1.0,
        simulated_closed: bool = False,
        target_corridor_id: Optional[str] = None,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Compute a travel-time matrix between locations (arbitrary coordinates or landmarks) using OSRM.
        Provides ground-truth input for VRP fleet optimization without any mock/demo cache fallbacks.
        """
        coords: List[Coords] = []
        names: List[str] = []
        effective_ids: List[str] = []

        if locations is not None and len(locations) > 0:
            coords = locations
            names = location_names if location_names and len(location_names) == len(locations) else [f"Location_{i}" for i in range(len(locations))]
            effective_ids = landmark_ids if landmark_ids and len(landmark_ids) == len(locations) else [f"loc_{i}" for i in range(len(locations))]
        elif landmark_ids is not None and len(landmark_ids) > 0:
            for lid in landmark_ids:
                lm = self.landmarks.get_by_id(lid)
                if not lm:
                    raise ValueError(f"Unknown landmark: '{lid}'")
                coords.append(Coords(lat=lm.lat, lon=lm.lon))
                names.append(lm.name)
            effective_ids = landmark_ids
        else:
            raise ValueError("Provide either landmark_ids or locations for travel_time_matrix")

        start_time = time.time()
        try:
            matrix = await self._provider.table(coords)
            if not matrix.durations_s or len(matrix.durations_s) != len(coords):
                raise ValueError("Incomplete or empty matrix from routing provider")
        except Exception as e:
            raise ValueError(f"Routing provider ({self._provider_name}) table generation failed: {str(e)}")

        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        fused_matrix = self.data_fusion.evaluate_matrix_traffic(
            landmark_ids=effective_ids,
            durations_s=matrix.durations_s,
            distances_m=matrix.distances_m,
            matrix_generation_ms=elapsed_ms,
            simulated_incident_multiplier=simulated_incident_multiplier,
            simulated_closed=simulated_closed,
            target_corridor_id=target_corridor_id
        )
        fused_matrix["landmark_names"] = names
        fused_matrix["computation_ms"] = elapsed_ms
        fused_matrix["matrix_metadata"] = {
            "source": self._provider_name,
            "provider": self._provider_name,
            "profile": "driving-car"
        }
        fused_matrix["provenance"] = {
            **self.provenance.get_metadata(),
            "routing_provider": self._provider_name,
            "traffic_provider": "TomTom"
        }
        return fused_matrix

    async def get_traffic_feed(self) -> Dict[str, Any]:
        """Returns live TomTom traffic flow observations and incidents for Visakhapatnam."""
        snapshot = await self.traffic_provider.get_flow()
        incidents = await self.traffic_provider.get_incidents()
        self.data_fusion.ingest_traffic_snapshot(snapshot, incidents)
        all_canonical = self.canonical_roads.get_all()
        return {
            "status": "SUCCESS",
            "provider": "TomTom",
            "snapshot": snapshot.model_dump(),
            "traffic_snapshot": snapshot.model_dump(),
            "incidents": [inc.model_dump() for inc in incidents],
            "canonical_corridors_count": len(all_canonical),
            "canonical_segments": [
                {
                    "id": seg.canonical_edge_id,
                    "name": seg.name,
                    "is_available": seg.is_available,
                    "speed_ratio": seg.speed_ratio,
                    "congestion_tier": seg.congestion_tier,
                    "observed_speed_kmh": seg.observed_speed_kmh,
                    "closure_reason": seg.closure_reason
                }
                for seg in all_canonical
            ]
        }

    async def get_traffic_snapshot(self) -> Dict[str, Any]:
        """Returns explicit timestamped traffic telemetry snapshot conforming to specifications."""
        snapshot = await self.traffic_provider.get_flow()
        incidents = await self.traffic_provider.get_incidents()
        all_canonical = self.canonical_roads.get_all()
        return {
            "status": snapshot.source_status,
            "provider": snapshot.provider,
            "observed_at": snapshot.observed_at,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "source_status": snapshot.source_status,
            "traffic_source_type": snapshot.traffic_source_type,
            "segments_updated": snapshot.segments_updated,
            "canonical_corridors_count": len(all_canonical),
            "observations_count": len(snapshot.observations),
            "incidents_count": len(incidents),
            "observations": [o.model_dump() for o in snapshot.observations],
            "incidents": [i.model_dump() for i in incidents],
            "provenance": {
                "traffic_source": snapshot.source_status,
                "provider": snapshot.provider,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    async def get_system_status(self) -> Dict[str, Any]:
        """Returns live system health and provider status."""
        traffic_health = await self.traffic_provider.health_check()
        traffic_status = "LIVE" if traffic_health else "UNAVAILABLE"
        return {
            "routing_engine": {
                "provider": self._provider_name,
                "status": "ACTIVE",
                "type": "road_network_ch"
            },
            "traffic_source": {
                "provider": "TomTom",
                "status": traffic_status
            },
            "network_source": {
                "provider": "OpenStreetMap",
                "status": "ACTIVE"
            },
            "provenance": {
                **self.provenance.get_metadata(),
                "traffic_provider": "TomTom",
                "routing_provider": self._provider_name
            }
        }

    async def debug_route(
        self,
        origin_query: str,
        dest_query: str,
        origin_lat: Optional[float] = None,
        origin_lon: Optional[float] = None,
        dest_lat: Optional[float] = None,
        dest_lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        QA Route Trace debug endpoint returning full coordinates, access points,
        snap distances, road names, and OSRM route metrics (Directive 7).
        """
        # 1. Resolve origin
        orig_res: Optional[PlaceResolution] = None
        if origin_lat is not None and origin_lon is not None:
            orig_res = await self.place_resolver.resolve_place(
                name=origin_query or "Origin",
                lat=origin_lat,
                lon=origin_lon
            )
        else:
            orig_search = await self.search_provider.search_places(origin_query, limit=1)
            if not orig_search:
                orig_geo = await self.search_provider.geocode_forward(origin_query)
                if orig_geo:
                    orig_search = [orig_geo]
            if orig_search:
                orig_res = await self.place_resolver.resolve_from_search_result(orig_search[0])
            else:
                # Check landmark registry as fallback
                lm = self.landmarks.search(origin_query)
                if lm:
                    orig_res = await self.place_resolver.resolve_place(name=lm[0].name, lat=lm[0].lat, lon=lm[0].lon)
                else:
                    raise ValueError(f"Origin location '{origin_query}' could not be resolved.")

        # 2. Resolve destination
        dest_res: Optional[PlaceResolution] = None
        if dest_lat is not None and dest_lon is not None:
            dest_res = await self.place_resolver.resolve_place(
                name=dest_query or "Destination",
                lat=dest_lat,
                lon=dest_lon
            )
        else:
            dest_search = await self.search_provider.search_places(dest_query, limit=1)
            if not dest_search:
                dest_geo = await self.search_provider.geocode_forward(dest_query)
                if dest_geo:
                    dest_search = [dest_geo]
            if dest_search:
                dest_res = await self.place_resolver.resolve_from_search_result(dest_search[0])
            else:
                lm = self.landmarks.search(dest_query)
                if lm:
                    dest_res = await self.place_resolver.resolve_place(name=lm[0].name, lat=lm[0].lat, lon=lm[0].lon)
                else:
                    raise ValueError(f"Destination location '{dest_query}' could not be resolved.")

        # 3. Route between resolved access coordinates
        route_data = await self.route_by_coords(
            origin_lat=orig_res.latitude,
            origin_lon=orig_res.longitude,
            dest_lat=dest_res.latitude,
            dest_lon=dest_res.longitude,
            origin_name=orig_res.name,
            dest_name=dest_res.name,
            origin_resolution=orig_res,
            dest_resolution=dest_res
        )

        primary = route_data.get("primary_route", {})
        return {
            "origin": {
                "query": origin_query,
                "provider": "TomTom",
                "name": orig_res.name,
                "address": orig_res.address,
                "lat": orig_res.latitude,
                "lon": orig_res.longitude,
                "snapped_lat": orig_res.access_latitude,
                "snapped_lon": orig_res.access_longitude,
                "snap_distance_m": orig_res.snap_distance_m,
                "road_name": orig_res.access_road_name,
                "confidence": orig_res.confidence,
                "resolution_method": orig_res.resolution_method
            },
            "destination": {
                "query": dest_query,
                "provider": "TomTom",
                "name": dest_res.name,
                "address": dest_res.address,
                "lat": dest_res.latitude,
                "lon": dest_res.longitude,
                "snapped_lat": dest_res.access_latitude,
                "snapped_lon": dest_res.access_longitude,
                "snap_distance_m": dest_res.snap_distance_m,
                "road_name": dest_res.access_road_name,
                "confidence": dest_res.confidence,
                "resolution_method": dest_res.resolution_method
            },
            "route": {
                "distance_m": primary.get("distance_m", 0.0),
                "distance_km": primary.get("distance_km", 0.0),
                "duration_s": primary.get("duration_s", 0.0),
                "base_duration_min": primary.get("free_flow_duration_min", 0.0),
                "duration_min": primary.get("duration_min", 0.0),
                "traffic_duration_min": primary.get("traffic_duration_min", 0.0),
                "traffic_delay_min": primary.get("traffic_delay_min", 0.0),
                "traffic_state": primary.get("traffic_freshness", "UNAVAILABLE"),
                "speed_sanity": route_data.get("speed_sanity", {}),
                "why_this_route": route_data.get("why_this_route", "")
            },
            "trace_13_metrics": {
                "tomtom_origin_lat": orig_res.latitude,
                "tomtom_origin_lon": orig_res.longitude,
                "tomtom_dest_lat": dest_res.latitude,
                "tomtom_dest_lon": dest_res.longitude,
                "osrm_origin_snapped_lat": orig_res.access_latitude,
                "osrm_origin_snapped_lon": orig_res.access_longitude,
                "osrm_dest_snapped_lat": dest_res.access_latitude,
                "osrm_dest_snapped_lon": dest_res.access_longitude,
                "origin_snap_distance_m": orig_res.snap_distance_m,
                "dest_snap_distance_m": dest_res.snap_distance_m,
                "osrm_route_distance_m": primary.get("distance_m", 0.0),
                "osrm_route_duration_s": primary.get("duration_s", 0.0),
                "route_geometry_length_m": primary.get("distance_m", 0.0)
            }
        }