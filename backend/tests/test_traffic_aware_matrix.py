"""
Unit Test: Traffic-Aware Travel-Time Matrix Fusion.

Verifies:
1. Baseline matrix T0 matches OSRM base routing duration.
2. Injected congestion shock (e.g. 3.0x on Beach Road) increases travel time between coastal landmarks (RK Beach <-> Rushikonda).
3. Unrelated inland pairs (NAD Junction <-> Pendurthi) maintain exact baseline routing duration.
4. Active corridor closure triggers forced inland detour penalty.
5. Timing telemetry explicitly separates matrix_generation_ms from traffic_fusion_ms.
"""

import pytest
from transport.canonical_roads import DataFusionEngine, CanonicalRoadRegistry


def test_traffic_aware_matrix_fusion():
    registry = CanonicalRoadRegistry()
    engine = DataFusionEngine(registry)
    landmarks = ["maddilapalem_junction", "rk_beach", "rushikonda_beach", "nad_junction"]

    # Mock baseline OSRM table
    durations_s = [
        [0.0, 600.0, 750.0, 900.0],
        [600.0, 0.0, 654.0, 1100.0],
        [750.0, 654.0, 0.0, 1300.0],
        [900.0, 1100.0, 1300.0, 0.0]
    ]
    distances_m = [
        [0.0, 6000.0, 10000.0, 9500.0],
        [6000.0, 0.0, 10570.0, 12000.0],
        [10000.0, 10570.0, 0.0, 14000.0],
        [9500.0, 12000.0, 14000.0, 0.0]
    ]

    # 1. Baseline evaluation (multiplier = 1.0)
    base = engine.evaluate_matrix_traffic(
        landmark_ids=landmarks,
        durations_s=durations_s,
        distances_m=distances_m,
        matrix_generation_ms=120.5,
        simulated_incident_multiplier=1.0,
        simulated_closed=False
    )
    assert base["status"] == "SUCCESS"
    assert base["affected_pairs_count"] == 0
    assert base["matrix_metadata"]["traffic_state"] == "BASELINE_FREE_FLOW"
    assert base["durations_s"][1][2] == 654.0  # RK Beach <-> Rushikonda unchanged

    # 2. Traffic Shock on Beach Road (3.0x congestion multiplier)
    shock = engine.evaluate_matrix_traffic(
        landmark_ids=landmarks,
        durations_s=durations_s,
        distances_m=distances_m,
        matrix_generation_ms=120.5,
        simulated_incident_multiplier=3.0,
        simulated_closed=False,
        target_corridor_id="beach_road"
    )
    assert shock["status"] == "SUCCESS"
    assert shock["affected_pairs_count"] > 0
    assert shock["matrix_metadata"]["traffic_state"] == "DEMO_CONGESTION_SHOCK"

    # RK Beach (idx 1) <-> Rushikonda (idx 2) duration must increase
    assert shock["durations_s"][1][2] > base["durations_s"][1][2]

    # Inland pair: Maddilapalem (0) <-> NAD Junction (3) must remain unaffected
    assert shock["durations_s"][0][3] == base["durations_s"][0][3]

    # Verify timing telemetry separation
    telemetry = shock["telemetry"]
    assert "matrix_generation_ms" in telemetry
    assert "traffic_fusion_ms" in telemetry
    assert telemetry["matrix_generation_ms"] == 120.5
    assert telemetry["traffic_fusion_ms"] >= 0.0


def test_corridor_closure_detour_in_matrix():
    registry = CanonicalRoadRegistry()
    engine = DataFusionEngine(registry)
    landmarks = ["rk_beach", "rushikonda_beach"]
    durations_s = [[0.0, 654.0], [654.0, 0.0]]
    distances_m = [[0.0, 10570.0], [10570.0, 0.0]]

    closed = engine.evaluate_matrix_traffic(
        landmark_ids=landmarks,
        durations_s=durations_s,
        distances_m=distances_m,
        simulated_closed=True,
        target_corridor_id="beach_road"
    )
    assert closed["matrix_metadata"]["traffic_state"] == "INCIDENT_CLOSURE_DETOUR"
    # Forced detour factor 2.05x on time, 1.38x on distance
    assert closed["durations_s"][0][1] == round(654.0 * 2.05, 1)
    assert closed["distances_m"][0][1] == round(10570.0 * 1.38, 1)
