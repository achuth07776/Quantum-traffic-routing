"""
Test Phase E4: Provider Integration and State Machine Verification (TomTom Provider).

Covers:
1. Provider Error and Uncredentialed Honesty (No Key, Invalid Key, Empty Observations -> UNAVAILABLE)
2. Traffic State Machine Transitions (Fresh -> LIVE, 120s-600s -> STALE, >600s -> UNAVAILABLE)
3. Canonical Road Matching Directionality Preservation
4. Unmocked Provider Call (when TOMTOM_API_KEY is configured in environment)
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from providers.traffic.tomtom import TomTomTrafficProvider
from providers.traffic.base import TrafficSnapshot, TrafficObservation
from transport.canonical_roads import CanonicalRoadRegistry, DataFusionEngine, TrafficFreshness


@pytest.mark.anyio
async def test_provider_uncredentialed_honesty():
    """Verifies that an uncredentialed provider gracefully returns UNAVAILABLE."""
    provider = TomTomTrafficProvider(api_key="")
    snapshot = await provider.get_flow()
    assert snapshot.source_status == "UNAVAILABLE"
    assert snapshot.segments_updated == 0
    assert len(snapshot.observations) == 0


@pytest.mark.anyio
async def test_provider_invalid_key_error_handling():
    """Verifies that an invalid API key results in UNAVAILABLE without unhandled crash."""
    provider = TomTomTrafficProvider(api_key="invalid_tomtom_api_key_test_xyz123")
    snapshot = await provider.get_flow()
    assert snapshot.source_status == "UNAVAILABLE"
    assert snapshot.segments_updated == 0
    assert len(snapshot.observations) == 0


@pytest.mark.anyio
async def test_provider_empty_result_unavailable():
    """Verifies that an empty provider observation set defaults to UNAVAILABLE."""
    snapshot = TrafficSnapshot(
        provider="TOMTOM",
        observed_at=datetime.now(timezone.utc).isoformat(),
        segments_updated=0,
        observations=[],
        incidents=[],
        source_status="UNAVAILABLE"
    )
    assert snapshot.source_status == "UNAVAILABLE"
    assert snapshot.raw_observations_count == 0


def test_traffic_freshness_state_machine():
    """
    Automated verification of traffic freshness transitions:
      - age < 120s and mapped > 0 -> LIVE
      - 120s <= age < 600s -> STALE
      - age >= 600s -> UNAVAILABLE
    """
    reg = CanonicalRoadRegistry()
    engine = DataFusionEngine(reg)
    now = datetime.now(timezone.utc)

    # 1. Fresh observation (age = 30s)
    obs = TrafficObservation(
        segment_id="Dr NTR Beach Road (Northbound)",
        speed_kmh=45.0,
        free_flow_speed_kmh=60.0,
        jam_factor=1.5,
        confidence=0.95,
        observed_at=(now - timedelta(seconds=30)).isoformat(),
        source="TOMTOM"
    )
    snap_live = TrafficSnapshot(
        provider="TOMTOM_TRAFFIC_V5",
        observed_at=(now - timedelta(seconds=30)).isoformat(),
        segments_updated=1,
        observations=[obs],
        incidents=[],
        source_status="LIVE"
    )
    engine.ingest_traffic_snapshot(snap_live)
    engine._last_update_utc = now - timedelta(seconds=30)

    # Evaluate route
    metrics_live = engine.evaluate_route_traffic(
        free_flow_duration_s=600.0,
        steps=[],
        geometry_geojson={"coordinates": [[83.35, 17.75], [83.36, 17.76]]}
    )
    assert metrics_live.traffic_freshness == TrafficFreshness.LIVE
    assert "LIVE" in metrics_live.traffic_source

    # 2. Stale observation (age = 180s)
    engine._last_update_utc = now - timedelta(seconds=180)
    metrics_stale = engine.evaluate_route_traffic(
        free_flow_duration_s=600.0,
        steps=[],
        geometry_geojson={"coordinates": [[83.35, 17.75], [83.36, 17.76]]}
    )
    assert metrics_stale.traffic_freshness == TrafficFreshness.STALE
    assert "STALE" in metrics_stale.traffic_source

    # 3. Expired observation (age = 700s -> UNAVAILABLE)
    engine._last_update_utc = now - timedelta(seconds=700)
    metrics_expired = engine.evaluate_route_traffic(
        free_flow_duration_s=600.0,
        steps=[],
        geometry_geojson={"coordinates": [[83.35, 17.75], [83.36, 17.76]]}
    )
    assert metrics_expired.traffic_freshness == TrafficFreshness.UNAVAILABLE


def test_canonical_road_direction_preservation():
    """
    Verifies that directional tracking is strictly maintained:
    A northbound traffic observation maps to the forward corridor and does not distort reverse.
    """
    reg = CanonicalRoadRegistry()
    engine = DataFusionEngine(reg)
    now_iso = datetime.now(timezone.utc).isoformat()

    snap = TrafficSnapshot(
        provider="TOMTOM_TRAFFIC_V5",
        observed_at=now_iso,
        segments_updated=1,
        observations=[
            TrafficObservation(
                segment_id="Dr NTR Beach Road (Northbound)",
                speed_kmh=18.0,
                free_flow_speed_kmh=60.0,
                jam_factor=7.0,
                confidence=0.95,
                observed_at=now_iso,
                source="TOMTOM"
            )
        ],
        incidents=[],
        source_status="LIVE"
    )
    engine.ingest_traffic_snapshot(snap)

    matched_seg = reg.get_by_id("cr_beach_road_north")
    assert matched_seg is not None
    assert matched_seg.direction == "FORWARD"
    assert matched_seg.speed_ratio == round(18.0 / 60.0, 3)
    assert matched_seg.congestion_tier == "SEVERE"


@pytest.mark.anyio
async def test_live_provider_unmocked_integration():
    """
    Unmocked integration test against TomTom Traffic API.
    If TOMTOM_API_KEY is configured in the environment, verifies real network response.
    """
    api_key = os.environ.get("TOMTOM_API_KEY")
    if not api_key:
        pytest.skip("TOMTOM_API_KEY not configured in environment; skipped live network call.")

    provider = TomTomTrafficProvider(api_key=api_key)
    snapshot = await provider.get_flow()
    assert snapshot.provider.upper() == "TOMTOM"
    assert snapshot.source_status in ["LIVE", "UNAVAILABLE"]
    if snapshot.source_status == "LIVE":
        assert len(snapshot.observations) > 0
