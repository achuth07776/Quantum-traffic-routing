"""
Debug & Trace script logging the 13 required metrics for the 6 key corridors in Visakhapatnam:
1. Pendurthi -> Simhachalam (Hilltop Sanctum & Foothills)
2. Pendurthi -> RK Beach
3. Pendurthi -> Rushikonda
4. Gajuwaka -> RK Beach
5. MVP Colony -> NAD
6. NAD -> Simhachalam
"""

import sys
import os
import asyncio
import json

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx


CORRIDORS = [
    ("Pendurthi", "Simhachalam Devasthanam", 17.801206, 83.215257, 17.766343, 83.250476),
    ("Pendurthi", "Simhachalam Foothills", 17.801206, 83.215257, 17.772896, 83.244017),
    ("Pendurthi", "RK Beach", 17.801206, 83.215257, 17.7144, 83.3341),
    ("Pendurthi", "Rushikonda Beach", 17.801206, 83.215257, 17.7818, 83.3854),
    ("Gajuwaka Junction", "RK Beach", 17.6896, 83.2128, 17.7144, 83.3341),
    ("MVP Colony", "NAD Junction", 17.7441, 83.3412, 17.7482, 83.2189),
    ("NAD Junction", "Simhachalam Foothills", 17.7482, 83.2189, 17.772896, 83.244017),
]


async def run_corridor_audit():
    print("=" * 80)
    print("VISAKHAPATNAM 6-CORRIDOR ROUTE TRACE AUDIT (13 REQUIRED METRICS)")
    print("=" * 80)

    results = []

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=20.0) as client:
        for orig_name, dest_name, o_lat, o_lon, d_lat, d_lon in CORRIDORS:
            payload = {
                "origin": orig_name,
                "destination": dest_name,
                "origin_lat": o_lat,
                "origin_lon": o_lon,
                "dest_lat": d_lat,
                "dest_lon": d_lon
            }

            try:
                res = await client.post("/api/v1/route/debug", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    results.append(data)
                    orig = data["origin"]
                    dest = data["destination"]
                    route = data["route"]
                    t13 = data.get("trace_13_metrics", {})
                    print(f"\n[CORRIDOR] {orig_name} -> {dest_name}")
                    print(f"  1. Raw Origin Coords:              ({orig['lat']}, {orig['lon']})")
                    print(f"  2. Raw Dest Coords:                ({dest['lat']}, {dest['lon']})")
                    print(f"  3. Resolved Origin Access Coords:  ({orig['snapped_lat']}, {orig['snapped_lon']})")
                    print(f"  4. Origin Snap Distance:           {orig['snap_distance_m']} m")
                    print(f"  5. Origin Access Road Name:        {orig['road_name']}")
                    print(f"  6. Origin Confidence:              {orig['confidence']}")
                    print(f"  7. Resolved Dest Access Coords:    ({dest['snapped_lat']}, {dest['snapped_lon']})")
                    print(f"  8. Dest Snap Distance:             {dest['snap_distance_m']} m")
                    print(f"  9. Dest Access Road Name:          {dest['road_name']}")
                    print(f" 10. Dest Confidence:                {dest['confidence']}")
                    print(f" 11. OSRM Route Distance:            {route['distance_km']} km ({route['distance_m']} m)")
                    print(f" 12. OSRM Base Duration:             {route.get('base_duration_min', route['duration_min'])} min")
                    print(f" 13. Traffic Adjusted Duration:      {route['traffic_duration_min']} min")
                    print(f"     Traffic Delay:                  {route.get('traffic_delay_min', 0)} min")
                    print(f"     Traffic State:                  {route.get('traffic_state', 'N/A')}")
                    print(f"     Why This Route:                 {route.get('why_this_route', '')[:80]}...")
                else:
                    print(f"\n[ERROR] {orig_name} -> {dest_name}: HTTP {res.status_code} - {res.text}")
            except Exception as e:
                print(f"\n[EXCEPTION] {orig_name} -> {dest_name}: {e}")

    print("\n" + "=" * 80)
    print(f"Audit completed: {len(results)}/{len(CORRIDORS)} corridors traced successfully.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_corridor_audit())
