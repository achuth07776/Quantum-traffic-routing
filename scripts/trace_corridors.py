"""
Audit script tracing 4 real Visakhapatnam corridors.
Queries the running platform API and outputs exact mathematical traces:
- OSRM route geometry and turn-by-turn maneuvers (with real road names, no fake names)
- Free-flow base duration (OSRM)
- TomTom flow speeds and coverage %
- Queue and incident delays
- Final traffic-adjusted travel time
"""
import os
import json
import httpx

CORRIDORS = [
    ("pendurthi", "rk_beach", "Pendurthi -> RK Beach"),
    ("pendurthi", "rushikonda_beach", "Pendurthi -> Rushikonda Beach"),
    ("gajuwaka_junction", "rk_beach", "Gajuwaka Junction -> RK Beach"),
    ("mvp_colony", "nad_junction", "MVP Colony -> NAD Junction"),
]

def run_trace():
    results = []
    base_url = "http://127.0.0.1:8000/api/v1/route/realworld"

    print("=" * 80)
    print("VISAKHAPATNAM 4-CORRIDOR ROUTING & TRAFFIC ACCURACY AUDIT")
    print("=" * 80)

    for orig_id, dest_id, label in CORRIDORS:
        payload = {
            "origin_id": orig_id,
            "destination_id": dest_id,
            "alternatives": True
        }
        try:
            resp = httpx.post(base_url, json=payload, timeout=30.0)
            if resp.status_code != 200:
                print(f"FAILED {label}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            primary = data.get("primary_route", {})
            prov = data.get("traffic_provenance", {})
            reroute = data.get("traffic_rerouting", {})
            steps = primary.get("steps", [])

            # Verify no fake names
            has_arterial_segment = any("arterial segment" in s.get("instruction", "").lower() or "arterial segment" in s.get("road_name", "").lower() for s in steps)
            assert not has_arterial_segment, f"Found Arterial Segment in {label}"

            trace_info = {
                "corridor": label,
                "origin": data.get("origin", {}).get("name"),
                "destination": data.get("destination", {}).get("name"),
                "distance_km": primary.get("distance_km"),
                "free_flow_min": primary.get("free_flow_duration_min"),
                "free_flow_avg_kmh": round((primary.get("distance_km", 0) / (primary.get("free_flow_duration_min", 1) / 60.0)), 1) if primary.get("free_flow_duration_min") else 0,
                "traffic_duration_min": primary.get("traffic_duration_min"),
                "traffic_avg_kmh": round((primary.get("distance_km", 0) / (primary.get("traffic_duration_min", 1) / 60.0)), 1) if primary.get("traffic_duration_min") else 0,
                "traffic_delay_min": primary.get("traffic_delay_min"),
                "traffic_freshness": primary.get("traffic_freshness"),
                "traffic_source": primary.get("traffic_source"),
                "coverage_pct": prov.get("route_coverage_pct"),
                "avg_current_speed_kmh": prov.get("avg_current_speed_kmh"),
                "avg_free_flow_speed_kmh": prov.get("avg_free_flow_speed_kmh"),
                "incidents_count": prov.get("incidents_on_route_count"),
                "is_rerouted": reroute.get("is_rerouted"),
                "reroute_reason": reroute.get("reroute_reason"),
                "step_count": len(steps),
                "sample_steps": [s.get("instruction") for s in steps[:5]]
            }
            results.append(trace_info)

            print(f"\n[{label}]")
            print(f"  Distance:               {trace_info['distance_km']} km")
            print(f"  OSRM Free-Flow Base:    {trace_info['free_flow_min']} min (~{trace_info['free_flow_avg_kmh']} km/h)")
            print(f"  TomTom Live Flow Speed: {trace_info['avg_current_speed_kmh']} km/h (Free: {trace_info['avg_free_flow_speed_kmh']} km/h, Coverage: {trace_info['coverage_pct']}%)")
            print(f"  Traffic Delay:          +{trace_info['traffic_delay_min']} min (Incidents on route: {trace_info['incidents_count']})")
            print(f"  Final Traffic Duration: {trace_info['traffic_duration_min']} min (~{trace_info['traffic_avg_kmh']} km/h)")
            print(f"  Traffic Freshness:      {trace_info['traffic_freshness']} ({trace_info['traffic_source']})")
            print(f"  Sample Steps (first 5):")
            for i, st in enumerate(trace_info['sample_steps'], 1):
                print(f"    {i}. {st}")

        except Exception as e:
            print(f"ERROR {label}: {e}")

    out_path = os.path.join(os.path.dirname(__file__), "corridor_traces.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nTraces written to {out_path}")

if __name__ == "__main__":
    run_trace()
