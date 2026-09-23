import asyncio
import json
import httpx
from app.main import _load_env
_load_env()
from providers.routing.osrm import OSRMRoutingProvider
from providers.routing.base import Coords
from transport.landmarks import LandmarkRegistry
from providers.traffic.tomtom import TomTomTrafficProvider
from app.services.realworld_routing_service import RealWorldRoutingService

async def trace():
    landmarks = LandmarkRegistry()
    service = RealWorldRoutingService(landmark_registry=landmarks)
    
    orig = landmarks.get_by_id('pendurthi')
    dest = landmarks.get_by_id('rk_beach')
    print(f"Landmark Origin: {orig}")
    print(f"Landmark Destination: {dest}")
    
    osrm = OSRMRoutingProvider()
    snapped_orig = await osrm.nearest(Coords(lat=orig.lat, lon=orig.lon))
    snapped_dest = await osrm.nearest(Coords(lat=dest.lat, lon=dest.lon))
    print(f"Snapped Origin: {snapped_orig}")
    print(f"Snapped Destination: {snapped_dest}")
    
    # Direct OSRM query
    url = f"https://router.project-osrm.org/route/v1/driving/{orig.lon},{orig.lat};{dest.lon},{dest.lat}?overview=full&geometries=geojson&steps=true&alternatives=true"
    print(f"\nOSRM URL: {url}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
        print(f"OSRM code: {data.get('code')}")
        routes = data.get("routes", [])
        print(f"OSRM routes count: {len(routes)}")
        for i, r in enumerate(routes):
            dist_km = r.get("distance", 0) / 1000.0
            dur_s = r.get("duration", 0)
            dur_min = dur_s / 60.0
            speed_kmh = (dist_km / (dur_min / 60.0)) if dur_min > 0 else 0
            print(f"  Route {i}: dist={dist_km:.2f} km, dur={dur_min:.2f} min, speed={speed_kmh:.1f} km/h")
            legs = r.get("legs", [])
            steps = legs[0].get("steps", []) if legs else []
            print(f"    Steps count: {len(steps)}")
            for s_idx, s in enumerate(steps[:8]):
                name = s.get("name")
                man = s.get("maneuver", {})
                print(f"      Step {s_idx}: name='{name}', type='{man.get('type')}', modifier='{man.get('modifier')}', dist={s.get('distance')}m, dur={s.get('duration')}s")

    # Trace TomTom traffic observations on this bounding box
    min_lat = min(orig.lat, dest.lat) - 0.02
    max_lat = max(orig.lat, dest.lat) + 0.02
    min_lon = min(orig.lon, dest.lon) - 0.02
    max_lon = max(orig.lon, dest.lon) + 0.02
    bbox = (min_lon, min_lat, max_lon, max_lat)
    print(f"\nTomTom Query BBox: {bbox}")
    
    tomtom = TomTomTrafficProvider()
    print(f"TomTom API Key Configured: {bool(tomtom.api_key and tomtom.api_key.strip())}")
    incidents = await tomtom.get_incidents(bbox)
    print(f"TomTom Incidents: {len(incidents)}")
    for inc in incidents:
        print(f"  Incident: {inc.type} - {inc.description} at ({inc.lat}, {inc.lon})")
        
    flow = await tomtom.get_flow(bbox)
    print(f"TomTom Flow Observations: {len(flow.observations)}")
    for obs in flow.observations[:5]:
        print(f"  Flow: {obs.segment_id} speed={obs.speed_kmh} free_flow={obs.free_flow_speed_kmh} jam={obs.jam_factor}")
        
    # Now trace the full routing service call
    res = await service.route_by_landmarks("pendurthi", "rk_beach", alternatives=True)
    print("\n--- Routing Service Output ---")
    pr = res.get("primary_route", {})
    print(f"Status: {res.get('status')}")
    print(f"Provider: {res.get('provider')}")
    print(f"Distance: {pr.get('distance_km')} km")
    print(f"Base Duration: {pr.get('free_flow_duration_min')} min")
    print(f"Traffic Duration: {pr.get('traffic_duration_min')} min")
    print(f"Traffic Delay: {pr.get('traffic_delay_min')} min")
    print(f"Traffic Source: {pr.get('traffic_source')}")
    print(f"Traffic Freshness: {pr.get('traffic_freshness')}")
    print(f"Rerouted: {res.get('traffic_rerouting', {}).get('is_rerouted')}")
    print(f"Reroute Reason: {res.get('traffic_rerouting', {}).get('reroute_reason')}")
    # Also test with TomTom place search coordinates:
    p_orig = Coords(lat=17.801206, lon=83.215257) # Pendurthi, Visakhapatnam from TomTom
    p_dest = Coords(lat=17.712454, lon=83.318403) # RK Beach from TomTom
    res_coords = await service.route_by_coords(
        origin_lat=p_orig.lat,
        origin_lon=p_orig.lon,
        dest_lat=p_dest.lat,
        dest_lon=p_dest.lon,
        origin_name="Pendurthi",
        dest_name="RK Beach",
        alternatives=True
    )
    pr_c = res_coords.get("primary_route", {})
    print("\n--- Route By TomTom Search Coords Output ---")
    print(f"Distance: {pr_c.get('distance_km')} km")
    print(f"Base Duration: {pr_c.get('free_flow_duration_min')} min")
    print(f"Traffic Duration: {pr_c.get('traffic_duration_min')} min")
    print(f"Traffic Delay: {pr_c.get('traffic_delay_min')} min")
    print(f"Speed: {pr_c.get('distance_km') / (pr_c.get('duration_min') / 60.0):.1f} km/h")
    print("Steps Sample:")
    for s in pr_c.get("steps", [])[:6]:
        print(f"  Instruction: '{s.get('instruction')}', Road Name: '{s.get('road_name')}'")

if __name__ == "__main__":
    asyncio.run(trace())
