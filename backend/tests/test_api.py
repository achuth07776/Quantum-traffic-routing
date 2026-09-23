import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_api_health_check(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "Visakhapatnam" in data["system"]


def test_api_get_network_geojson(client):
    res = client.get("/api/v1/network?graph_id=visakhapatnam_network")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0


def test_api_optimize_route(client):
    payload = {
        "graph_id": "visakhapatnam_network",
        "origin_node": "1", # RK Beach
        "destination_node": "6", # Rushikonda IT SEZ
        "algorithms": ["dijkstra", "astar", "aco", "qpso"],
        "weights": {"time": 0.5, "distance": 0.2, "congestion": 0.2, "emissions": 0.1},
        "max_iterations": 25,
        "population_size": 15,
        "seed": 42
    }
    res = client.post("/api/v1/route/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "dijkstra" in data["results"]
    assert "qpso" in data["results"]
    assert data["results"]["dijkstra"]["is_feasible"] is True
    assert data["results"]["qpso"]["is_feasible"] is True
    assert "provenance" in data


def test_api_optimize_vrp_fleet(client):
    payload = {
        "problem_id": "vizag_fleet_api_test",
        "graph_id": "visakhapatnam_network",
        "depot_node": "4", # Maddilapalem
        "customers": [
            {"node_id": "1", "name": "RK Beach Hub", "demand_kg": 100.0, "time_window_start_min": 0.0, "time_window_end_min": 120.0, "service_duration_min": 10.0},
            {"node_id": "2", "name": "Siripuram Store", "demand_kg": 80.0, "time_window_start_min": 0.0, "time_window_end_min": 90.0, "service_duration_min": 10.0},
            {"node_id": "5", "name": "MVP Colony Retail", "demand_kg": 90.0, "time_window_start_min": 0.0, "time_window_end_min": 100.0, "service_duration_min": 10.0}
        ],
        "num_vehicles": 2,
        "vehicle_capacity_kg": 300.0,
        "max_iterations": 20,
        "population_size": 15,
        "seed": 42
    }
    res = client.post("/api/v1/vrp/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "qpso" in data
    assert "qpso_routes_geojson" in data
    assert len(data["qpso"]["routes"]) > 0


def test_api_incident_injection_and_reset(client):
    incident_payload = {
        "graph_id": "visakhapatnam_network",
        "u": "4",
        "v": "5",
        "incident_type": "ROAD_BLOCK",
        "multiplier": 1.0,
        "is_closed": True
    }
    res_inc = client.post("/api/v1/traffic/incident", json=incident_payload)
    assert res_inc.status_code == 200
    inc_data = res_inc.json()
    assert inc_data["is_closed"] is True

    # Reset
    res_reset = client.post("/api/v1/traffic/reset?graph_id=visakhapatnam_network")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "SUCCESS"


def test_api_get_scenarios(client):
    res = client.get("/api/v1/simulation/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
    assert any("Maddilapalem" in s["title"] for s in data)


def test_api_quantum_qaoa_execution(client):
    payload = {
        "problem_name": "vizag_ambulance_fire_dispatch",
        "num_variables": 4,
        "variable_labels": ["Amb_BeachRoad", "Amb_BRTS", "Fire_BeachRoad", "Fire_BRTS"],
        "q_matrix": [
            [-5.0, 20.0, 15.0,  0.0],
            [ 0.0, -2.0,  0.0,  0.0],
            [ 0.0,  0.0, -4.0, 20.0],
            [ 0.0,  0.0,  0.0, -1.0]
        ],
        "p_layers": 2
    }
    res = client.post("/api/v1/quantum/qaoa", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["qubit_count"] == 4
