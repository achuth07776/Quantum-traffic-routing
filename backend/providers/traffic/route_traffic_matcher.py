"""
Route Traffic Matcher.

Matches TomTom Traffic Flow geometries to OSRM route geometries using Shapely
LineStrings and metric projection. Computes true segment-level traffic travel time:
    T_traffic = sum(L_i / v_i)
for matched microsegments, and preserves proportional base OSRM duration for
unmatched segments.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Union
from shapely.geometry import LineString, Point


@dataclass
class FlowObservation:
    current_speed_kmh: float
    free_flow_speed_kmh: float
    confidence: float = 1.0
    road_closure: bool = False
    coordinates_latlon: List[Tuple[float, float]] = field(default_factory=list)


def project_xy(lat: float, lon: float, lat0: float, lon0: float) -> Tuple[float, float]:
    """
    Project (lat, lon) in degrees to local (x, y) in metres
    using equirectangular projection centered around (lat0, lon0).
    """
    mean_lat_rad = math.radians(lat0)
    x = (lon - lon0) * 111139.0 * math.cos(mean_lat_rad)
    y = (lat - lat0) * 111139.0
    return (x, y)


def densify(
    coords_lon_lat: List[Union[Tuple[float, float], List[float]]],
    spacing_m: float = 60.0
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Subdivides route polyline into microsegments of maximum length ~spacing_m.
    Returns list of ((lon1, lat1), (lon2, lat2)) pairs.
    """
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    if not coords_lon_lat or len(coords_lon_lat) < 2:
        return segments

    for i in range(len(coords_lon_lat) - 1):
        p1 = (float(coords_lon_lat[i][0]), float(coords_lon_lat[i][1]))
        p2 = (float(coords_lon_lat[i + 1][0]), float(coords_lon_lat[i + 1][1]))
        lon1, lat1 = p1
        lon2, lat2 = p2

        # Compute geodesic/equirectangular distance between vertices
        mean_lat = math.radians((lat1 + lat2) / 2.0)
        dx = (lon2 - lon1) * 111139.0 * math.cos(mean_lat)
        dy = (lat2 - lat1) * 111139.0
        seg_dist = math.sqrt(dx * dx + dy * dy)

        if seg_dist <= spacing_m or seg_dist < 1e-3:
            segments.append((p1, p2))
        else:
            num_sub = max(1, int(math.ceil(seg_dist / spacing_m)))
            prev_pt = p1
            for s in range(1, num_sub + 1):
                t = s / float(num_sub)
                curr_lon = lon1 + t * (lon2 - lon1)
                curr_lat = lat1 + t * (lat2 - lat1)
                curr_pt = (curr_lon, curr_lat)
                segments.append((prev_pt, curr_pt))
                prev_pt = curr_pt

    return segments


def match_flow_to_route(
    coords_lon_lat: List[Union[Tuple[float, float], List[float]]],
    base_duration_s: float,
    flow_observations: List[FlowObservation],
    tolerance_m: float = 60.0,
    incidents: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    True geometry-aware traffic flow matching.
    
    1. Densifies route into ~60m microsegments.
    2. Projects microsegments and flow observations into metric Cartesian space.
    3. Matches microsegments to flow LineStrings where max(line_distance, midpoint_distance) <= tolerance_m.
    4. Computes matched travel time strictly as L_i / v_i.
    5. Preserves proportional base OSRM duration for unmatched segments.
    6. Identifies blocked routes and handles incident queue delays without double counting.
    """
    safe_base_duration = max(1.0, float(base_duration_s))

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
            "traffic_duration_s": safe_base_duration,
            "traffic_delay_s": 0.0,
            "avg_current_speed_kmh": 0.0,
            "avg_free_flow_speed_kmh": 0.0,
            "confidence": 0.0,
            "incidents_count": 0,
            "is_blocked": False,
            "block_reason": None,
        }

    # Midpoint for local metric projection
    all_lats = [float(c[1]) for c in coords_lon_lat]
    all_lons = [float(c[0]) for c in coords_lon_lat]
    lat0 = sum(all_lats) / len(all_lats)
    lon0 = sum(all_lons) / len(all_lons)

    # Densify route into ~60m microsegments
    microsegments = densify(coords_lon_lat, spacing_m=60.0)
    if not microsegments:
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
            "traffic_duration_s": safe_base_duration,
            "traffic_delay_s": 0.0,
            "avg_current_speed_kmh": 0.0,
            "avg_free_flow_speed_kmh": 0.0,
            "confidence": 0.0,
            "incidents_count": 0,
            "is_blocked": False,
            "block_reason": None,
        }

    # Build projected Shapely objects for route microsegments
    route_items = []
    total_route_length_m = 0.0

    for (p1, p2) in microsegments:
        x1, y1 = project_xy(p1[1], p1[0], lat0, lon0)
        x2, y2 = project_xy(p2[1], p2[0], lat0, lon0)
        length_m = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length_m < 1e-4:
            continue
        total_route_length_m += length_m
        line = LineString([(x1, y1), (x2, y2)])
        midpoint = Point((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        route_items.append({
            "line": line,
            "midpoint": midpoint,
            "length_m": length_m,
            "p1": p1,
            "p2": p2,
        })

    total_route_length_m = max(1.0, total_route_length_m)

    # Build projected Shapely objects for flow observations
    flow_items = []
    for obs in flow_observations:
        pts = []
        for lat, lon in obs.coordinates_latlon:
            pts.append(project_xy(lat, lon, lat0, lon0))

        flow_geom = None
        if len(pts) >= 2:
            try:
                flow_geom = LineString(pts)
            except Exception:
                flow_geom = None
        elif len(pts) == 1:
            flow_geom = Point(pts[0])

        if flow_geom is not None:
            flow_items.append({
                "geom": flow_geom,
                "obs": obs,
            })

    matched_segments = 0
    unmatched_segments = 0
    matched_length_m = 0.0
    unmatched_length_m = 0.0
    matched_durations_s: List[float] = []
    unmatched_durations_s: List[float] = []
    current_speeds: List[float] = []
    free_speeds: List[float] = []
    confidences: List[float] = []
    matched_micro_indices = set()

    for idx, r_item in enumerate(route_items):
        r_line = r_item["line"]
        r_mid = r_item["midpoint"]
        r_len = r_item["length_m"]

        best_flow = None
        best_dist = float("inf")

        for f_item in flow_items:
            f_geom = f_item["geom"]
            try:
                d_line = r_line.distance(f_geom)
                d_mid = r_mid.distance(f_geom)
                d_test = max(d_line, d_mid)
                if d_test <= tolerance_m and d_test < best_dist:
                    best_dist = d_test
                    best_flow = f_item["obs"]
            except Exception:
                continue

        if best_flow is not None:
            matched_segments += 1
            matched_length_m += r_len
            matched_micro_indices.add(idx)

            # Effective speed capped by free flow speed
            effective_speed_kmh = min(best_flow.current_speed_kmh, best_flow.free_flow_speed_kmh)
            # Ensure minimum crawl speed of 3.0 km/h
            effective_speed_kmh = max(3.0, effective_speed_kmh)

            speed_ms = (effective_speed_kmh * 1000.0) / 3600.0
            t_seg = r_len / speed_ms
            matched_durations_s.append(t_seg)

            current_speeds.append(best_flow.current_speed_kmh)
            free_speeds.append(best_flow.free_flow_speed_kmh)
            confidences.append(best_flow.confidence)
        else:
            unmatched_segments += 1
            unmatched_length_m += r_len
            # Unmatched segment preserves proportional base OSRM duration
            t_base_seg = safe_base_duration * (r_len / total_route_length_m)
            unmatched_durations_s.append(t_base_seg)

    coverage_pct = round((matched_length_m / total_route_length_m) * 100.0, 1)

    # Base traffic duration from segments
    total_flow_duration_s = sum(matched_durations_s) + sum(unmatched_durations_s)

    # Incident processing
    is_blocked = False
    block_reason = None
    additional_incident_delay_s = 0.0
    matched_incidents_count = 0

    if incidents:
        for inc in incidents:
            inc_lat = getattr(inc, "lat", None)
            inc_lon = getattr(inc, "lon", None)
            if inc_lat is None or inc_lon is None:
                continue

            inc_x, inc_y = project_xy(float(inc_lat), float(inc_lon), lat0, lon0)
            inc_pt = Point(inc_x, inc_y)

            # Check distance to any microsegment of the route
            min_dist_to_route = float("inf")
            closest_micro_idx = -1
            for r_idx, r_item in enumerate(route_items):
                d = r_item["line"].distance(inc_pt)
                if d < min_dist_to_route:
                    min_dist_to_route = d
                    closest_micro_idx = r_idx

            if min_dist_to_route <= tolerance_m:
                matched_incidents_count += 1
                inc_type = str(getattr(inc, "type", "")).upper()
                inc_desc = str(getattr(inc, "description", "Traffic restriction"))

                if "CLOSURE" in inc_type or "CLOSED" in inc_desc.upper():
                    is_blocked = True
                    block_reason = f"Road closure: {inc_desc}"
                else:
                    # Prevent double counting: only add delay if the microsegment near incident is NOT matched by flow
                    if closest_micro_idx not in matched_micro_indices:
                        inc_delay = float(getattr(inc, "delay_seconds", 0.0) or 0.0)
                        if inc_delay > 0.0:
                            additional_incident_delay_s += min(600.0, inc_delay)

    final_traffic_duration_s = round(total_flow_duration_s + additional_incident_delay_s, 1)
    traffic_delay_s = round(max(0.0, final_traffic_duration_s - safe_base_duration), 1)

    # Traffic state classification
    if matched_segments == 0 or len(flow_observations) == 0:
        state = "UNAVAILABLE"
    elif coverage_pct < 60.0:
        state = "PARTIAL"
    else:
        state = "LIVE"

    avg_curr_spd = round(sum(current_speeds) / len(current_speeds), 1) if current_speeds else 0.0
    avg_free_spd = round(sum(free_speeds) / len(free_speeds), 1) if free_speeds else 0.0
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    return {
        "provider": "TomTom",
        "state": state,
        "observations_used": len(flow_observations),
        "coverage_pct": coverage_pct,
        "traffic_coverage_pct": coverage_pct,
        "matched_length_m": round(matched_length_m, 1),
        "route_length_m": round(total_route_length_m, 1),
        "matched_segments": matched_segments,
        "unmatched_segments": unmatched_segments,
        "traffic_duration_s": final_traffic_duration_s,
        "traffic_delay_s": traffic_delay_s,
        "avg_current_speed_kmh": avg_curr_spd,
        "avg_free_flow_speed_kmh": avg_free_spd,
        "confidence": avg_conf,
        "incidents_count": matched_incidents_count,
        "is_blocked": is_blocked,
        "block_reason": block_reason,
    }
