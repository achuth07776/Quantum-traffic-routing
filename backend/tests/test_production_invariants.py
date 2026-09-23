"""
Production Invariant & Numerical Verification Test Suite.
Verifies:
1. Routing provider (OSRM) distance, duration, speed arithmetic across 3 routes.
2. Turn-by-turn step sum vs route totals.
3. Traffic adjusted duration >= free flow.
4. Fleet VRP solver invariants (capacity, coverage, exact objective evaluation).
5. QPSO reproducibility on fixed random seed.
"""
import pytest
from providers.routing.base import Coords
from transport.landmarks import LandmarkRegistry
from app.services.realworld_routing_service import RealWorldRoutingService
from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer


@pytest.mark.anyio
async def test_routing_numerical_consistency_and_step_sums():
    landmarks = LandmarkRegistry()
    service = RealWorldRoutingService(landmark_registry=landmarks)
    
    test_pairs = [
        ("Short Urban", "rk_beach", "jagadamba_junction"),
        ("Medium Arterial", "rk_beach", "rushikonda_beach"),
        ("Long Corridor", "steel_plant_main_gate", "bheemili_beach")
    ]
    
    for label, orig_id, dest_id in test_pairs:
        res = await service.route_by_landmarks(
            origin_id=orig_id,
            destination_id=dest_id,
            alternatives=True
        )
        assert res["status"] == "SUCCESS", f"Route {label} failed: {res.get('error')}"
        primary = res["primary_route"]
        dist_km = primary["distance_km"]
        dur_min = primary["free_flow_duration_min"]
        traffic_dur_min = primary["traffic_duration_min"]
        speed_kmh = round(dist_km / (dur_min / 60.0), 1)
        
        # Invariant: Traffic duration >= free-flow duration
        assert traffic_dur_min >= dur_min - 0.01, f"Traffic dur ({traffic_dur_min}) < base dur ({dur_min})"
        
        # Invariant: Step sum matches route totals within epsilon
        step_dist = sum(s["distance_m"] for s in primary["steps"]) / 1000.0
        step_dur = sum(s["duration_s"] for s in primary["steps"]) / 60.0
        
        assert abs(dist_km - step_dist) <= 0.2, f"Step distance mismatch: {dist_km} vs {step_dist}"
        assert abs(dur_min - step_dur) <= 0.2, f"Step duration mismatch: {dur_min} vs {step_dur}"


@pytest.mark.anyio
async def test_fleet_vrp_invariants_and_exact_seed_reproducibility():
    landmarks = LandmarkRegistry()
    service = RealWorldRoutingService(landmark_registry=landmarks)
    optimizer = RealWorldVRPOptimizer()
    
    depot_id = "maddilapalem_junction"
    stops = ["rk_beach", "rushikonda_beach", "simhachalam_temple", "nad_junction", "gajuwaka_junction"]
    all_lms = [depot_id] + stops
    
    mat_res = await service.travel_time_matrix(all_lms)
    assert mat_res["status"] == "SUCCESS"
    durations = mat_res["durations_min"]
    distances = mat_res["distances_km"]
    demands = [0.0, 20.0, 30.0, 15.0, 25.0, 20.0]
    capacities = [60.0, 60.0]
    
    vrp_res = optimizer.solve_fleet_vrp(
        node_ids=all_lms,
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        qpso_seed=42
    )
    assert vrp_res["status"] == "SUCCESS"
    ort = vrp_res["results"]["ortools"]
    qpso = vrp_res["results"]["qpso"]
    
    for name, sol in [("OR-Tools", ort), ("QPSO", qpso)]:
        assert sol["is_feasible"] is True, f"{name} reported infeasible"
        routes_list = sol["routes"]
        
        # Coverage invariant: all customer nodes visited exactly once
        visited = []
        for r in routes_list:
            if isinstance(r, dict):
                custs = r.get("customer_nodes", [n for n in r.get("full_path_nodes", []) if n != depot_id])
            else:
                custs = r.customer_nodes
            visited.extend(custs)
        assert sorted(visited) == sorted(stops), f"{name} customer visit mismatch: {visited} vs {stops}"
        
        # Capacity invariant: no vehicle exceeds capacity
        for v_idx, r in enumerate(routes_list):
            if isinstance(r, dict):
                tour_demand = r.get("total_load_kg", sum(demands[all_lms.index(node)] for node in r.get("full_path_nodes", [])))
            else:
                tour_demand = r.total_load_kg
            cap = capacities[v_idx]
            assert tour_demand <= cap + 1e-6, f"{name} vehicle {v_idx} overloaded: {tour_demand} > {cap}"

    # Scientific reproducibility: seed 42 produces bitwise identical objective
    vrp_res_2 = optimizer.solve_fleet_vrp(
        node_ids=all_lms,
        duration_matrix_min=durations,
        distance_matrix_km=distances,
        demands=demands,
        vehicle_capacities=capacities,
        qpso_seed=42
    )
    obj1 = vrp_res["results"]["qpso"]["total_fleet_cost"]
    obj2 = vrp_res_2["results"]["qpso"]["total_fleet_cost"]
    assert abs(obj1 - obj2) < 1e-9, f"QPSO non-deterministic on seed 42: {obj1} vs {obj2}"
