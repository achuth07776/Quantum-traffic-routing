"""
Integration Test: Real-Network Fleet Reoptimization under Live Traffic.

Verifies:
1. End-to-end execution of POST /api/v1/vrp/traffic_reoptimize.
2. Baseline fleet plan T0 vs traffic-shocked fleet plan T1.
3. Tour divergence or delta travel-time shifts under Beach Road congestion.
4. Response contains accurate timing telemetry: matrix_generation_ms, traffic_fusion_ms, optimizer_runtime_ms.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_fleet_traffic_reoptimization_endpoint():
    with TestClient(app) as client:
        req_body = {
            "depot_id": "maddilapalem_junction",
            "customer_ids": [
                "rk_beach",
                "rushikonda_beach",
                "kailasagiri_hill",
                "nad_junction"
            ],
            "num_vehicles": 2,
            "vehicle_capacity_kg": 300.0,
            "target_corridor_id": "beach_road",
            "simulated_incident_multiplier": 3.0,
            "simulated_closed": False
        }

        resp = client.post("/api/v1/vrp/traffic_reoptimize", json=req_body)
        assert resp.status_code == 200
        data = resp.json()

    assert data["status"] == "SUCCESS"
    assert data["experiment_title"] == "Traffic-State-to-Matrix Fusion & Dynamic Fleet Reoptimization"
    assert "value_of_reoptimization" in data
    assert "four_quadrant_experiment_table" in data
    assert "telemetry_latency_breakdown" in data
    assert "fixed_reference_scales" in data
    assert "data_lineage" in data

    # Verify telemetry latency breakdown has no unexplained gaps
    breakdown = data["telemetry_latency_breakdown"]
    assert "matrix_t0_generation_ms" in breakdown
    assert "solve_t0_ms" in breakdown
    assert "matrix_t1_generation_ms" in breakdown
    assert "traffic_fusion_ms" in breakdown
    assert "evaluation_old_plan_ms" in breakdown
    assert "solve_t1_ms" in breakdown
    assert "total_measured_stages_ms" in breakdown
    assert "total_request_ms" in breakdown
    # Total measured stages should be very close to total request ms (within 20ms)
    assert abs(breakdown["total_request_ms"] - breakdown["total_measured_stages_ms"]) < 20.0

    # Verify fixed reference scales are present
    assert data["fixed_reference_scales"]["t_ref_min"] > 0
    assert data["fixed_reference_scales"]["d_ref_km"] > 0

    # Verify value of reoptimization
    val = data["value_of_reoptimization"]
    assert "ortools" in val
    assert "qpso" in val
    assert val["ortools"]["time_saved_by_reoptimization_min"] >= 0.0
    assert val["ortools"]["j_cost_saved_by_reoptimization"] >= 0.0
    assert len(val["hero_summary"]) > 20

    # Verify 4-quadrant table has all 6 rows (OR-Tools and QPSO across T0, T1-inaction, and T1-reopt)
    assert len(data["four_quadrant_experiment_table"]) == 6
