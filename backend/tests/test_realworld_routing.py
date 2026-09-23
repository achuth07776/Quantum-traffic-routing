import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_get_landmarks(client):
    response = client.get("/api/v1/landmarks")
    assert response.status_code == 200
    data = response.json()
    assert "landmarks" in data
    assert len(data["landmarks"]) >= 20
    
    # Verify landmark structure
    lm = data["landmarks"][0]
    assert "id" in lm
    assert "name" in lm
    assert "lat" in lm
    assert "lon" in lm
    assert "category" in lm


def test_search_landmarks(client):
    response = client.get("/api/v1/landmarks?query=beach")
    assert response.status_code == 200
    data = response.json()
    assert len(data["landmarks"]) >= 2
    for lm in data["landmarks"]:
        assert "beach" in lm["name"].lower() or "beach" in lm["id"].lower()


def test_system_status(client):
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "routing_engine" in data
    assert "traffic_source" in data
    assert "network_source" in data
    assert data["network_source"]["provider"] == "OpenStreetMap"


def test_realworld_routing_by_landmarks(client):
    # Test routing between RK Beach and Rushikonda Beach
    response = client.post(
        "/api/v1/route/realworld",
        json={
            "origin_id": "rk_beach",
            "destination_id": "rushikonda_beach",
            "alternatives": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    # Check response structure
    assert data["status"] in ["SUCCESS", "NO_ROUTE", "ERROR"]
    if data["status"] == "SUCCESS":
        assert "primary_route" in data
        route = data["primary_route"]
        assert route["distance_m"] > 0
        assert route["duration_s"] > 0
        assert "geometry_geojson" in route
        assert route["geometry_geojson"]["type"] == "LineString"
        assert len(route["geometry_geojson"]["coordinates"]) > 0
        assert "provenance" in data


def test_realworld_routing_invalid_landmarks(client):
    response = client.post(
        "/api/v1/route/realworld",
        json={
            "origin_id": "non_existent_landmark_123",
            "destination_id": "rushikonda_beach"
        }
    )
    assert response.status_code == 400


def test_realworld_travel_time_matrix(client):
    response = client.post(
        "/api/v1/route/matrix",
        json={
            "landmark_ids": ["rk_beach", "siripuram_junction", "maddilapalem_junction"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["SUCCESS", "ERROR"]
    if data["status"] == "SUCCESS":
        assert "durations_s" in data
        assert len(data["durations_s"]) == 3
        assert len(data["durations_s"][0]) == 3


def test_get_live_traffic(client):
    response = client.get("/api/v1/traffic/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "traffic_snapshot" in data
    assert "incidents" in data
    assert data["canonical_corridors_count"] >= 5


def test_realworld_routing_with_traffic_data_fusion(client):
    response = client.post(
        "/api/v1/route/realworld",
        json={
            "origin_id": "rk_beach",
            "destination_id": "rushikonda_beach",
            "simulated_multiplier": 2.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    primary = data["primary_route"]
    assert "free_flow_duration_s" in primary
    assert "traffic_duration_s" in primary
    assert "traffic_delay_s" in primary
    assert primary["traffic_duration_s"] > primary["free_flow_duration_s"]
    assert "traffic_source" in primary
    assert primary["traffic_freshness"] in ["LIVE", "STALE", "FALLBACK", "DEMO"]


def test_realworld_vrp_with_ortools_benchmark(client):
    response = client.post(
        "/api/v1/vrp/realworld",
        json={
            "depot_id": "maddilapalem_junction",
            "customer_ids": ["rk_beach", "rushikonda_beach", "nad_junction", "kailasagiri_hill"],
            "customer_demands": [40.0, 50.0, 30.0, 25.0],
            "num_vehicles": 2,
            "vehicle_capacity_kg": 250.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "benchmark_comparison" in data
    assert "results" in data
    assert "ortools" in data["results"]
    assert "qpso" in data["results"]
    assert "greedy" in data["results"]
    assert data["results"]["ortools"]["is_feasible"] is True
    assert data["results"]["qpso"]["is_feasible"] is True
    assert data["results"]["greedy"]["is_feasible"] is True
    assert "objective" in data["results"]["ortools"]
    assert "objective" in data["results"]["qpso"]
    assert "objective_function" in data["benchmark_comparison"]

    # Verify mathematical consistency of the cost gap
    ortools_cost = data["results"]["ortools"]["objective"]["objective_value"]
    qpso_cost = data["results"]["qpso"]["objective"]["objective_value"]
    expected_gap = round((qpso_cost - ortools_cost) / max(1e-6, ortools_cost) * 100.0, 2)
    reported_gap = data["benchmark_comparison"]["qpso_gap_vs_reference_pct"]
    assert abs(expected_gap - reported_gap) < 0.05


def test_matrix_vrp_unreachable_cells():
    from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer
    optimizer = RealWorldVRPOptimizer()
    node_ids = ["maddilapalem", "rk_beach", "rushikonda"]
    # Node 1 and Node 2 are unreachable from each other (None)
    durations = [[0.0, 12.0, 18.0], [12.0, 0.0, None], [18.0, None, 0.0]]
    distances = [[0.0, 4.5, 9.2], [4.5, 0.0, None], [9.2, None, 0.0]]
    demands = [0.0, 50.0, 50.0]
    caps = [100.0, 100.0]

    res = optimizer.solve_fleet_vrp(node_ids, durations, distances, demands, caps)
    assert res["status"] == "SUCCESS"
    assert res["results"]["ortools"]["is_feasible"] is True
    # The route between rk_beach and rushikonda must never be traversed
    for route in res["results"]["ortools"]["routes"]:
        stops = route["full_path_nodes"]
        for k in range(len(stops) - 1):
            pair = (stops[k], stops[k+1])
            assert pair != ("rk_beach", "rushikonda")
            assert pair != ("rushikonda", "rk_beach")


def test_geocoding_and_snapping(client):
    response = client.get("/api/v1/geocode?q=rushikonda")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "result" in data
    assert "place_name" in data["result"]
    assert "snapped_road" in data["result"]
    assert data["result"]["snapped_road"]["snap_quality"] in ["GOOD", "ACCEPTABLE", "WARNING", "REVIEW_LOCATION"]


def test_snap_distance_quality_warning(client):
    # Kailasagiri is a hilltop park located >500m from Beach Road
    response = client.get("/api/v1/geocode?q=kailasagiri")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "result" in data
    snap_info = data["result"]["snapped_road"]
    assert snap_info["snap_distance_m"] > 500.0
    assert snap_info["snap_quality"] == "REVIEW_LOCATION"
    assert snap_info["snap_warning"] is not None
    assert "Location snapped" in snap_info["snap_warning"]


def test_traffic_snapshot_endpoint(client):
    response = client.get("/api/v1/traffic/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["LIVE", "STALE", "FALLBACK", "UNAVAILABLE"]
    assert "provider" in data
    assert "observed_at" in data
    assert "received_at" in data
    assert "segments_updated" in data
    assert "incidents" in data
    assert "canonical_corridors_count" in data


def test_dynamic_traffic_rerouting(client):
    # On multi-route corridor Pendurthi -> RK Beach, severe incident dynamically switches to alternative
    payload = {
        "origin_id": "pendurthi",
        "destination_id": "rk_beach",
        "alternatives": True,
        "simulated_closed": True
    }
    response = client.post("/api/v1/route/realworld", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "traffic_rerouting" in data
    assert data["traffic_rerouting"]["is_rerouted"] is True
    assert "Dynamic Rerouting" in data["traffic_rerouting"]["reroute_reason"]
    # Alternative corridor route distance is ~22.65 km
    assert data["primary_route"]["distance_km"] > 21.0


def test_vrp_missing_demand_rejected(client):
    # Enforces Item 12: Delivery demand required for each customer stop
    response = client.post(
        "/api/v1/vrp/realworld",
        json={
            "depot_id": "maddilapalem_junction",
            "customer_ids": ["rk_beach", "rushikonda_beach"],
            "num_vehicles": 2
        }
    )
    assert response.status_code == 400
    assert "Delivery demand required" in response.json().get("detail", "")


def test_vrp_arbitrary_customer_places(client):
    # Enforces Item 17: Fleet accepts arbitrary searched locations
    response = client.post(
        "/api/v1/vrp/realworld",
        json={
            "depot": {"name": "Central Hub", "lat": 17.7348, "lon": 83.3245},
            "customers": [
                {"name": "Customer North", "lat": 17.7818, "lon": 83.3854, "demand_kg": 45.0},
                {"name": "Customer South", "lat": 17.7144, "lon": 83.3341, "demand_kg": 60.0}
            ],
            "num_vehicles": 2,
            "vehicle_capacity_kg": 150.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert len(data["stops_metadata"]) == 3


def test_normalized_vrp_objective(client):
    # Validates normalized objective J = w_t * (T / T_ref) + w_d * (D / D_ref)
    payload = {
        "depot_id": "maddilapalem_junction",
        "customer_ids": ["rk_beach", "rushikonda_beach", "nad_junction", "visakhapatnam_port"],
        "customer_demands": [35.0, 45.0, 55.0, 60.0],
        "num_vehicles": 2
    }
    response = client.post("/api/v1/vrp/realworld", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    bench = data["benchmark_comparison"]
    assert "objective_function" in bench
    obj_fn = bench["objective_function"]
    assert obj_fn["name"] == "normalized_weighted_travel_cost"
    assert "reference_scales" in obj_fn
    assert obj_fn["reference_scales"]["t_ref_min"] > 0
    assert obj_fn["reference_scales"]["d_ref_km"] > 0
    assert "reference_solver" in bench
    assert "Google OR-Tools" in bench["reference_solver"]
    assert bench["qpso_cost_gap_vs_reference_pct"] is not None




