"""
Canonical Road Segment Model and Data Fusion Engine for Visakhapatnam.

Provides:
1. CanonicalRoadSegment: Directional road segment entity joining physical OSM geometry with dynamic traffic state.
   Supports speed ratios r = v_current / v_free and hard incident availability constraints.
2. CanonicalRoadRegistry: Curated major arterial corridors in Visakhapatnam.
3. DataFusionEngine: Merges real-time traffic observations (TomTom Traffic API) or fallback simulation (BPR)
   onto road network segments, evaluating travel time adjustments, freshness status, and route feasibility.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
from providers.traffic.base import TrafficObservation, IncidentReport, TrafficSnapshot


class CanonicalRoadSegment(BaseModel):
    """
    Standardized road segment entity joining physical OSM geometry with dynamic traffic state.
    Supports directional tracking (FORWARD / REVERSE), speed ratios (r = v_current / v_free),
    and incident-driven availability constraints (incident closure overrides flow).
    """
    canonical_edge_id: str
    name: str
    osm_way_id: Optional[str] = None
    road_class: str = "primary"  # motorway, trunk, primary, secondary
    oneway: bool = False
    direction: str = "FORWARD"   # FORWARD or REVERSE
    speed_limit_kmh: float = 50.0
    length_m: float
    start_coords: Tuple[float, float]  # (lat, lon)
    end_coords: Tuple[float, float]    # (lat, lon)
    is_available: bool = True
    closure_reason: Optional[str] = None
    speed_ratio: float = 1.0  # r = v_current / v_free (1.0 = free flow, 0.32 = severe delay)
    congestion_tier: str = "NORMAL"  # NORMAL (r>0.8), MODERATE (0.5<=r<=0.8), SEVERE (r<0.5)
    observed_speed_kmh: Optional[float] = None
    traffic: Optional[TrafficObservation] = None


class TrafficFreshness(str):
    LIVE = "LIVE"          # < 2 minutes old
    STALE = "STALE"        # 2 to 10 minutes old
    FALLBACK = "FALLBACK"  # > 10 minutes or simulation
    UNAVAILABLE = "UNAVAILABLE"  # No live provider observations


class FusedRouteMetrics(BaseModel):
    """
    Detailed traffic-aware metrics computed by the data fusion layer.
    Separates free-flow provider duration from live traffic delay.
    """
    free_flow_duration_s: float
    free_flow_duration_min: float
    traffic_duration_s: float
    traffic_duration_min: float
    traffic_delay_s: float
    traffic_delay_min: float
    traffic_source: str
    traffic_freshness: str
    observed_at: str
    confidence: float
    jam_factor_avg: float
    affected_segments_count: int
    traversed_corridors: List[str] = Field(default_factory=list)
    is_blocked: bool = False
    speed_ratio_avg: float = 1.0


class CanonicalRoadRegistry:
    """
    Curated registry of principal Visakhapatnam arterial corridors.
    Acts as the canonical bridge between OSM ways and traffic observation segments.
    """

    def __init__(self):
        self._segments: Dict[str, CanonicalRoadSegment] = {}
        self._initialize_canonical_corridors()

    def _initialize_canonical_corridors(self):
        corridors = [
            # 1. Beach Road South (RK Beach to Lawson's Bay)
            CanonicalRoadSegment(
                canonical_edge_id="cr_beach_road_south",
                name="Dr NTR Beach Road (Southbound)",
                osm_way_id="osm/beach_south",
                road_class="primary",
                oneway=False,
                direction="FORWARD",
                speed_limit_kmh=50.0,
                length_m=4200.0,
                start_coords=(17.7144, 83.3341), # RK Beach
                end_coords=(17.7348, 83.3450)     # Lawson's Bay
            ),

            # 2. Beach Road North (Lawson's Bay to Rushikonda IT SEZ)
            CanonicalRoadSegment(
                canonical_edge_id="cr_beach_road_north",
                name="Dr NTR Beach Road (Northbound)",
                osm_way_id="osm/beach_north",
                road_class="primary",
                oneway=False,
                direction="FORWARD",
                speed_limit_kmh=60.0,
                length_m=6400.0,
                start_coords=(17.7348, 83.3450), # Lawson's Bay
                end_coords=(17.7818, 83.3854)     # Rushikonda IT SEZ
            ),

            # 3. Waltair Main Road (Maddilapalem to Siripuram)
            CanonicalRoadSegment(
                canonical_edge_id="cr_maddilapalem_siripuram",
                name="Waltair Main Road",
                osm_way_id="osm/waltair_main",
                road_class="primary",
                oneway=False,
                direction="FORWARD",
                speed_limit_kmh=45.0,
                length_m=2800.0,
                start_coords=(17.7348, 83.3245), # Maddilapalem
                end_coords=(17.7226, 83.3156)     # Siripuram
            ),

            # 4. NH-16 Arterial Corridor (Health City Bypass)
            CanonicalRoadSegment(
                canonical_edge_id="cr_nh16_maddilapalem_rushikonda",
                name="NH-16 Arterial Corridor (Health City Bypass)",
                osm_way_id="osm/nh16_arterial",
                road_class="trunk",
                oneway=True,
                direction="FORWARD",
                speed_limit_kmh=80.0,
                length_m=11200.0,
                start_coords=(17.7348, 83.3245), # Maddilapalem
                end_coords=(17.7890, 83.3560)     # Madhurawada / Rushikonda Bypass
            ),

            # 5. Visakhapatnam Port Flyover / Scindia Corridor
            CanonicalRoadSegment(
                canonical_edge_id="cr_port_connectivity_road",
                name="Visakhapatnam Port Flyover / Scindia Corridor",
                osm_way_id="osm/port_flyover",
                road_class="trunk",
                oneway=False,
                direction="FORWARD",
                speed_limit_kmh=50.0,
                length_m=5800.0,
                start_coords=(17.6975, 83.2842), # Port Area
                end_coords=(17.6745, 83.2655)     # Scindia Junction
            ),

            # 6. Gajuwaka - Steel Plant Arterial Expressway
            CanonicalRoadSegment(
                canonical_edge_id="cr_gajuwaka_industrial_expressway",
                name="Gajuwaka - Steel Plant Arterial Expressway",
                osm_way_id="osm/gajuwaka_steel",
                road_class="trunk",
                oneway=False,
                direction="FORWARD",
                speed_limit_kmh=70.0,
                length_m=8600.0,
                start_coords=(17.6896, 83.2128), # Gajuwaka Junction
                end_coords=(17.6415, 83.1610)     # Steel Plant Main Gate
            ),

            # 7. Simhachalam BRTS Transit Corridor
            CanonicalRoadSegment(
                canonical_edge_id="cr_brts_simhachalam_corridor",
                name="Simhachalam BRTS Transit Corridor",
                osm_way_id="osm/simhachalam_brts",
                road_class="primary",
                oneway=False,
                direction="FORWARD",
                speed_limit_kmh=55.0,
                length_m=6200.0,
                start_coords=(17.7482, 83.2189), # NAD Junction
                end_coords=(17.7685, 83.2421)     # Simhachalam
            ),
        ]
        for c in corridors:
            self._segments[c.canonical_edge_id] = c

    def get_all(self) -> List[CanonicalRoadSegment]:
        return list(self._segments.values())

    def reset_all(self):
        """Resets all segments to clean free-flow available state."""
        for seg in self._segments.values():
            seg.traffic = None
            seg.speed_ratio = 1.0
            seg.congestion_tier = "NORMAL"
            seg.observed_speed_kmh = None
            seg.is_available = True
            seg.closure_reason = None

    def get_by_id(self, segment_id: str) -> Optional[CanonicalRoadSegment]:
        clean_id = segment_id.replace("_fwd", "").replace("_rev", "")
        return self._segments.get(clean_id)

    def find_matching_segment(self, lat: float, lon: float, tolerance_km: float = 3.0) -> Optional[CanonicalRoadSegment]:
        """Finds closest canonical corridor within spatial tolerance."""
        best_seg = None
        best_dist = float("inf")
        for seg in self._segments.values():
            d_start = ((seg.start_coords[0] - lat)**2 + (seg.start_coords[1] - lon)**2) ** 0.5 * 111.0
            d_end = ((seg.end_coords[0] - lat)**2 + (seg.end_coords[1] - lon)**2) ** 0.5 * 111.0
            min_d = min(d_start, d_end)
            if min_d < best_dist and min_d <= tolerance_km:
                best_dist = min_d
                best_seg = seg
        return best_seg

    def match_corridors_with_distance(
        self,
        steps: List[Any],
        geometry_geojson: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculates the distance in meters traveled along each unique canonical corridor.
        Uses geometry coordinate bounds (inland lon < 83.33 vs coastal lon >= 83.33)
        and turn-by-turn road steps to accurately partition traversed corridors.
        """
        is_inland_bypass = False
        if geometry_geojson and "coordinates" in geometry_geojson:
            coords = geometry_geojson["coordinates"]
            if coords:
                min_lon = min(c[0] for c in coords)
                if min_lon < 83.33:
                    is_inland_bypass = True

        corridor_dists: Dict[str, float] = {}
        accum_dist = 0.0

        for step in steps:
            rname = getattr(step, "road_name", "") if hasattr(step, "road_name") else (step.get("road_name", "") if isinstance(step, dict) else "")
            instr = getattr(step, "instruction", "") if hasattr(step, "instruction") else (step.get("instruction", "") if isinstance(step, dict) else "")
            s_dist = getattr(step, "distance_m", 0.0) if hasattr(step, "distance_m") else (step.get("distance_m", 0.0) if isinstance(step, dict) else 0.0)
            text = f"{rname} {instr}".lower()

            if is_inland_bypass:
                if accum_dist < 2000.0 and ("beach" in text or "unnamed" in text or rname in ["", "Unnamed road"]):
                    corridor_dists["cr_beach_road_south"] = corridor_dists.get("cr_beach_road_south", 0.0) + s_dist
                else:
                    corridor_dists["cr_nh16_maddilapalem_rushikonda"] = corridor_dists.get("cr_nh16_maddilapalem_rushikonda", 0.0) + s_dist
            else:
                if "beach" in text or rname in ["", "Unnamed road", "unnamed road"] or "unnamed" in text or "rushikonda" in text:
                    if accum_dist < 4300.0:
                        cid = "cr_beach_road_south"
                    else:
                        cid = "cr_beach_road_north"
                    corridor_dists[cid] = corridor_dists.get(cid, 0.0) + s_dist
                elif any(k in text for k in ["waltair", "siripuram"]):
                    corridor_dists["cr_maddilapalem_siripuram"] = corridor_dists.get("cr_maddilapalem_siripuram", 0.0) + s_dist
                elif any(k in text for k in ["port", "scindia", "harbour"]):
                    corridor_dists["cr_port_connectivity_road"] = corridor_dists.get("cr_port_connectivity_road", 0.0) + s_dist
                elif any(k in text for k in ["steel plant", "gajuwaka"]):
                    corridor_dists["cr_gajuwaka_industrial_expressway"] = corridor_dists.get("cr_gajuwaka_industrial_expressway", 0.0) + s_dist
                elif any(k in text for k in ["simhachalam", "brts"]):
                    corridor_dists["cr_brts_simhachalam_corridor"] = corridor_dists.get("cr_brts_simhachalam_corridor", 0.0) + s_dist

            accum_dist += s_dist

        return corridor_dists

    def match_corridors_from_steps(
        self,
        steps: List[Any],
        geometry_geojson: Optional[Dict[str, Any]] = None
    ) -> List[CanonicalRoadSegment]:
        """Matches OSRM turn-by-turn maneuvers to canonical corridors traversed for >= 500m."""
        dists = self.match_corridors_with_distance(steps, geometry_geojson)
        matched = []
        for cid, dist in dists.items():
            if dist >= 500.0:
                seg = self.get_by_id(cid)
                if seg and seg not in matched:
                    matched.append(seg)
        return matched


class DataFusionEngine:
    """
    Data fusion engine merging road network topology with live observations & fallback simulation.
    Ensures clear separation between profile-routed base routing duration and live traffic travel times.
    Implements physical distance-weighted speed-ratio travel time scaling and hard incident closure constraints.
    """

    def __init__(self, registry: CanonicalRoadRegistry):
        self.registry = registry
        self._last_snapshot: Optional[TrafficSnapshot] = None
        self._last_update_utc: Optional[datetime] = None

    def ingest_traffic_snapshot(
        self,
        snapshot: TrafficSnapshot,
        incidents: Optional[List[IncidentReport]] = None
    ):
        """
        Updates internal traffic observations from a live or fallback traffic provider.
        Derives speed ratio r = v_current / v_free and applies incident availability constraints.
        """
        self._last_snapshot = snapshot
        self._last_update_utc = datetime.now(timezone.utc)

        # Reset road segment availability before applying snapshot incidents
        for seg in self.registry.get_all():
            seg.is_available = True
            seg.closure_reason = None

        # 1. Update speed ratios from observations
        for obs in snapshot.observations:
            v_free = max(5.0, obs.free_flow_speed_kmh)
            v_curr = max(0.0, obs.speed_kmh)
            r = round(v_curr / v_free, 3)

            tier = "NORMAL"
            if r < 0.5:
                tier = "SEVERE"
            elif r <= 0.8:
                tier = "MODERATE"

            for seg in self.registry.get_all():
                seg.name.lower()
                obs_id_lower = obs.segment_id.lower()
                # Check keyword match
                is_match = False
                if "south" in obs_id_lower and "south" in seg.canonical_edge_id:
                    is_match = True
                elif "north" in obs_id_lower and "north" in seg.canonical_edge_id:
                    is_match = True
                elif seg.name.lower() in obs_id_lower or obs_id_lower in seg.name.lower():
                    is_match = True

                if is_match:
                    seg.traffic = obs
                    seg.speed_ratio = r
                    seg.congestion_tier = tier
                    seg.observed_speed_kmh = v_curr

        # 2. Count mapped segments
        mapped_count = 0
        for seg in self.registry.get_all():
            if seg.traffic is not None:
                mapped_count += 1
        snapshot.mapped_segments_count = mapped_count
        snapshot.raw_observations_count = len(snapshot.observations)

        # 3. Apply incident constraints (Incident closure is a hard availability constraint)
        if incidents:
            for inc in incidents:
                if inc.type in ["ROAD_CLOSURE", "CLOSURE"] or inc.severity == "CRITICAL":
                    matched = self.registry.find_matching_segment(inc.lat, inc.lon, tolerance_km=3.5)
                    if matched:
                        matched.is_available = False
                        matched.closure_reason = f"Incident: {inc.description}"

    def evaluate_route_traffic(
        self,
        free_flow_duration_s: float,
        steps: List[Any],
        geometry_geojson: Optional[Dict[str, Any]] = None,
        simulated_incident_multiplier: float = 1.0,
        simulated_closed: bool = False,
        target_corridor_id: Optional[str] = None
    ) -> FusedRouteMetrics:
        """
        Calculates traffic-adjusted travel time by fusing OSRM route steps with
        available traffic observations or BPR fallback simulation on traversed corridors.
        Uses distance-weighted delay calculation to ensure realistic route impact.
        Derived traffic-adjustment model:
          traffic delay = t_free * (D_corridor / D_total) * (1 / max(0.20, r) - 1)
        """
        now = datetime.now(timezone.utc)
        observed_time_str = now.isoformat()
        traffic_source = "BPR_SIMULATION"
        freshness = TrafficFreshness.FALLBACK
        confidence = 0.80

        corridor_dists = self.registry.match_corridors_with_distance(steps, geometry_geojson)
        total_dist_m = sum(getattr(s, "distance_m", 0.0) for s in steps) if steps else 10000.0
        traversed_ids = list(corridor_dists.keys())

        # 1. Check if any traversed corridor is blocked by real incident or simulation
        is_blocked = False
        block_reason = None
        for cid, dist in corridor_dists.items():
            seg = self.registry.get_by_id(cid)
            # Must traverse the closed segment for at least 1000m to be blocked
            if seg and not seg.is_available and dist >= 1000.0:
                is_blocked = True
                block_reason = seg.closure_reason or f"Corridor {seg.name} is closed."
                break

        is_target_hit = True
        if target_corridor_id:
            is_target_hit = target_corridor_id in traversed_ids

        if simulated_closed and is_target_hit:
            is_blocked = True
            block_reason = "Simulated Corridor Incident Closure"

        if is_blocked:
            return FusedRouteMetrics(
                free_flow_duration_s=round(free_flow_duration_s, 1),
                free_flow_duration_min=round(free_flow_duration_s / 60.0, 1),
                traffic_duration_s=-1.0,
                traffic_duration_min=-1.0,
                traffic_delay_s=-1.0,
                traffic_delay_min=-1.0,
                traffic_source=block_reason or "INCIDENT_CLOSURE",
                traffic_freshness="DEMO" if simulated_closed else freshness,
                observed_at=observed_time_str,
                confidence=confidence,
                jam_factor_avg=10.0,
                affected_segments_count=len(traversed_ids),
                traversed_corridors=traversed_ids,
                is_blocked=True,
                speed_ratio_avg=0.0
            )

        # 2. Check live traffic freshness and mapped segments
        mapped_count = sum(1 for s in self.registry.get_all() if s.traffic is not None)

        if self._last_snapshot and self._last_update_utc:
            age_s = (now - self._last_update_utc).total_seconds()
            raw_obs = len(self._last_snapshot.observations)

            # Strict State Machine:
            # LIVE requires: source_status == "LIVE" AND raw_obs > 0 AND mapped_count > 0 AND age_s < 120s
            if (self._last_snapshot.source_status == "LIVE" and
                raw_obs > 0 and
                mapped_count > 0 and
                age_s < 120.0):
                freshness = TrafficFreshness.LIVE
                confidence = 0.95
                traffic_source = f"{self._last_snapshot.provider} (LIVE · {raw_obs} obs, {mapped_count} mapped)"
            elif age_s < 600.0 and self._last_snapshot.source_status in ["LIVE", "STALE"]:
                freshness = TrafficFreshness.STALE
                confidence = 0.70
                traffic_source = f"{self._last_snapshot.provider} (STALE · {int(age_s)}s old)"
            else:
                freshness = TrafficFreshness.UNAVAILABLE
                confidence = 0.0
                traffic_source = "UNAVAILABLE"
        else:
            freshness = TrafficFreshness.UNAVAILABLE
            confidence = 0.0
            traffic_source = "UNAVAILABLE"

        # 3. Calculate distance-weighted delay based on speed ratio r = v_curr / v_free
        traffic_delay_s = 0.0
        affected_count = 0
        speed_ratios_weighted = []
        jam_factor_sum = 0.0

        for cid, dist in corridor_dists.items():
            seg = self.registry.get_by_id(cid)
            if seg:
                if seg.traffic:
                    jam_factor_sum += seg.traffic.jam_factor
                if seg.speed_ratio is not None and seg.speed_ratio < 1.0:
                    # Physical traffic-to-travel-time transformation:
                    # For a road segment of length L_e with observed speed v_obs and free-flow speed v_free:
                    #   T_e = (L_e / v_obs) * 60 = t_free_e * (v_free / v_obs) = t_free_e * (1 / r)
                    # Delay component:
                    #   Delay_e = T_e - t_free_e = t_free_e * ((1 / r) - 1)
                    # where t_free_e = free_flow_duration_s * (dist / total_dist_m)
                    effective_r = max(0.20, seg.speed_ratio)
                    ratio_factor = (1.0 / effective_r) - 1.0
                    weight = min(1.0, dist / max(1.0, total_dist_m))
                    corridor_delay = free_flow_duration_s * weight * ratio_factor
                    traffic_delay_s += corridor_delay
                    affected_count += 1
                    speed_ratios_weighted.append(seg.speed_ratio)

        if traffic_delay_s > 0:
            traffic_duration_s = round(free_flow_duration_s + traffic_delay_s, 1)
            avg_r = round(sum(speed_ratios_weighted) / len(speed_ratios_weighted), 3)
            traffic_source = f"{traffic_source} (Observed speed ratio r={avg_r:.2f})"
        elif simulated_incident_multiplier > 1.0 and is_target_hit:
            freshness = "DEMO"
            traffic_duration_s = round(free_flow_duration_s * simulated_incident_multiplier, 1)
            traffic_delay_s = round(traffic_duration_s - free_flow_duration_s, 1)
            traffic_source = f"DEMO_SCENARIO (What-if shock {simulated_incident_multiplier:.1f}x)"
        else:
            traffic_duration_s = round(free_flow_duration_s, 1)
            traffic_delay_s = 0.0

        avg_speed_ratio = round(sum(speed_ratios_weighted) / max(1, len(speed_ratios_weighted)), 2) if speed_ratios_weighted else 1.0
        avg_jam = round(jam_factor_sum / max(1, len(corridor_dists)), 2) if corridor_dists else 0.0

        return FusedRouteMetrics(
            free_flow_duration_s=round(free_flow_duration_s, 1),
            free_flow_duration_min=round(free_flow_duration_s / 60.0, 1),
            traffic_duration_s=round(traffic_duration_s, 1),
            traffic_duration_min=round(traffic_duration_s / 60.0, 1),
            traffic_delay_s=round(traffic_delay_s, 1),
            traffic_delay_min=round(traffic_delay_s / 60.0, 1),
            traffic_source=traffic_source,
            traffic_freshness=freshness,
            observed_at=observed_time_str,
            confidence=confidence,
            jam_factor_avg=avg_jam,
            affected_segments_count=affected_count,
            traversed_corridors=traversed_ids,
            is_blocked=False,
            speed_ratio_avg=avg_speed_ratio
        )

    def evaluate_matrix_traffic(
        self,
        landmark_ids: List[str],
        durations_s: List[List[float]],
        distances_m: List[List[float]],
        matrix_generation_ms: float = 0.0,
        simulated_incident_multiplier: float = 1.0,
        simulated_closed: bool = False,
        target_corridor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transforms an OSRM NxN free-flow travel-time matrix into a traffic-aware matrix
        by fusing physical canonical corridor traffic states (speeds, delays, closures).

        Physical Delay Formulation:
          For any landmark pair (i, j) traversing corridor c:
            T_ij(traffic) = T_ij(free) + T_ij(free) * w_c * ((1 / max(0.20, r_c)) - 1)
          If corridor c is closed by incident:
            Direct pair is detoured (e.g. coastal -> inland detour factor 2.05x time, 1.38x distance).
        """
        fusion_t0 = datetime.now(timezone.utc)
        start_fusion_time = datetime.now().timestamp()

        # Known corridor-to-landmark topologies on Visakhapatnam road network
        corridor_clusters = {
            "beach_road": {
                "nodes": {"rk_beach", "kailasagiri_hill", "rushikonda_beach", "gitam_university", "bheemili_beach", "waltair_uplands", "rushikonda_tech_park"},
                "segments": ["cr_beach_road_south", "cr_beach_road_north"],
                "detour_time_factor": 2.05,
                "detour_dist_factor": 1.38
            },
            "nh16_inland": {
                "nodes": {"maddilapalem_junction", "nad_junction", "pendurthi", "madhurawada", "vims", "cmr_central_mall", "arilova_health_city", "pm_palem", "kommadhi", "anandapuram", "sujatha_nagar", "chinamushidiwada"},
                "segments": ["cr_nh16_inland_central", "cr_nh16_inland_north"],
                "detour_time_factor": 1.65,
                "detour_dist_factor": 1.25
            },
            "port_corridor": {
                "nodes": {"visakhapatnam_port", "scindia_junction", "king_george_hospital", "poorna_market", "mindi_terminal"},
                "segments": ["cr_port_arterial"],
                "detour_time_factor": 1.70,
                "detour_dist_factor": 1.20
            },
            "gajuwaka_corridor": {
                "nodes": {"gajuwaka_junction", "steel_plant_main_gate", "scindia_junction", "gajuwaka_autonagar", "gajuwaka_bhel", "kurmannapalem", "sheela_nagar"},
                "segments": ["cr_gajuwaka_expressway"],
                "detour_time_factor": 1.80,
                "detour_dist_factor": 1.30
            }
        }

        n = len(landmark_ids)
        if not durations_s or not distances_m or len(durations_s) < n or any(len(r) < n for r in durations_s):
            raise ValueError(f"Matrix dimension mismatch: expected at least {n}x{n}, got {len(durations_s)} rows")
        fused_durations_s = [row[:] for row in durations_s]
        fused_distances_m = [row[:] for row in distances_m]

        target_corridor = target_corridor_id or "beach_road"
        affected_pairs = 0
        state = "BASELINE_FREE_FLOW"

        # Check live corridor speeds in registry
        beach_segs = [self.registry.get_by_id(sid) for sid in corridor_clusters["beach_road"]["segments"]]
        live_ratios = [s.speed_ratio for s in beach_segs if s and s.speed_ratio is not None and s.speed_ratio < 1.0]

        (simulated_incident_multiplier > 1.0 or simulated_closed)

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                node_i = landmark_ids[i]
                node_j = landmark_ids[j]

                # Check if pair traverses Beach Road corridor
                if node_i in corridor_clusters["beach_road"]["nodes"] and node_j in corridor_clusters["beach_road"]["nodes"]:
                    orig_t = durations_s[i][j]
                    orig_d = distances_m[i][j]

                    if simulated_closed and target_corridor in ["beach_road", "all"]:
                        # Forced inland detour
                        fused_durations_s[i][j] = round(orig_t * corridor_clusters["beach_road"]["detour_time_factor"], 1)
                        fused_distances_m[i][j] = round(orig_d * corridor_clusters["beach_road"]["detour_dist_factor"], 1)
                        affected_pairs += 1
                        state = "INCIDENT_CLOSURE_DETOUR"
                    elif simulated_incident_multiplier > 1.0 and target_corridor in ["beach_road", "all"]:
                        # What-if congestion shock
                        weight = 0.85
                        fused_durations_s[i][j] = round(orig_t * (1.0 + weight * (simulated_incident_multiplier - 1.0)), 1)
                        affected_pairs += 1
                        state = "DEMO_CONGESTION_SHOCK"
                    elif live_ratios:
                        # Real-world traffic observation
                        avg_r = max(0.20, sum(live_ratios) / len(live_ratios))
                        ratio_factor = (1.0 / avg_r) - 1.0
                        fused_durations_s[i][j] = round(orig_t * (1.0 + 0.85 * ratio_factor), 1)
                        affected_pairs += 1
                        state = "LIVE_TRAFFIC_ADJUSTED"

        fusion_elapsed_ms = round((datetime.now().timestamp() - start_fusion_time) * 1000, 2)
        total_ms = round(matrix_generation_ms + fusion_elapsed_ms, 2)

        durations_min = [[round(s / 60.0, 2) for s in row] for row in fused_durations_s]
        distances_km = [[round(m / 1000.0, 2) for m in row] for row in fused_distances_m]

        matrix_ts = fusion_t0.strftime("%Y%m%d_%H%M%S")

        return {
            "status": "SUCCESS",
            "matrix_metadata": {
                "matrix_id": f"matrix_vizag_osm_{matrix_ts}",
                "traffic_snapshot_id": f"traffic_{matrix_ts}_{state.lower()}",
                "network_version": "osm_visakhapatnam_v2",
                "routing_engine": "osrm",
                "traffic_state": state,
                "demand_provenance": "Operator-configured delivery locations mapped to real road network",
                "created_at": fusion_t0.isoformat()
            },
            "durations_s": fused_durations_s,
            "distances_m": fused_distances_m,
            "durations_min": durations_min,
            "distances_km": distances_km,
            "affected_pairs_count": affected_pairs,
            "telemetry": {
                "matrix_generation_ms": matrix_generation_ms,
                "traffic_fusion_ms": fusion_elapsed_ms,
                "total_matrix_ms": total_ms
            }
        }
