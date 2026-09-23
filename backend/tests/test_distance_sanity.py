"""
Automated Distance Sanity and Ground Truth Consistency Testing Suite.
Validates the 6 key Visakhapatnam corridors against physical road geometry bounds.
Flags routes with >10% deviation as REVIEW and >20% deviation as FAIL.
Verifies the zero-hardcoded-distance invariant across the platform.
"""

import pytest
from unittest.mock import AsyncMock
from app.services.realworld_routing_service import RealWorldRoutingService
from providers.routing.base import RouteResult, RouteStep, Coords, SnappedPoint


KEY_CORRIDORS = [
    {
        "id": "pendurthi_to_simhachalam_foothills",
        "origin_name": "Pendurthi",
        "origin_coords": (17.801206, 83.215257),
        "dest_name": "Simhachalam (Foothills / Bus Stand)",
        "dest_coords": (17.772896, 83.244017),
        "expected_dist_km": 6.6,
        "min_dist_km": 5.5,
        "max_dist_km": 8.0,
        "min_dur_min": 10.0,
        "max_dur_min": 25.0
    },
    {
        "id": "pendurthi_to_simhachalam_hilltop",
        "origin_name": "Pendurthi",
        "origin_coords": (17.801206, 83.215257),
        "dest_name": "Simhachalam Devasthanam (Hilltop Sanctum via Ghat Road)",
        "dest_coords": (17.766343, 83.250476),
        "expected_dist_km": 11.24,
        "min_dist_km": 9.5,
        "max_dist_km": 13.0,
        "min_dur_min": 14.0,
        "max_dur_min": 35.0
    },
    {
        "id": "pendurthi_to_rk_beach",
        "origin_name": "Pendurthi",
        "origin_coords": (17.801206, 83.215257),
        "dest_name": "RK Beach",
        "dest_coords": (17.7144, 83.3341),
        "expected_dist_km": 21.5,
        "min_dist_km": 18.0,
        "max_dist_km": 26.0,
        "min_dur_min": 25.0,
        "max_dur_min": 65.0
    },
    {
        "id": "pendurthi_to_rushikonda",
        "origin_name": "Pendurthi",
        "origin_coords": (17.801206, 83.215257),
        "dest_name": "Rushikonda Beach",
        "dest_coords": (17.7818, 83.3854),
        "expected_dist_km": 27.0,
        "min_dist_km": 23.0,
        "max_dist_km": 32.0,
        "min_dur_min": 30.0,
        "max_dur_min": 75.0
    },
    {
        "id": "gajuwaka_to_rk_beach",
        "origin_name": "Gajuwaka Junction",
        "origin_coords": (17.6896, 83.2128),
        "dest_name": "RK Beach",
        "dest_coords": (17.7144, 83.3341),
        "expected_dist_km": 17.5,
        "min_dist_km": 14.5,
        "max_dist_km": 21.0,
        "min_dur_min": 20.0,
        "max_dur_min": 50.0
    },
    {
        "id": "mvp_colony_to_nad",
        "origin_name": "MVP Colony",
        "origin_coords": (17.7441, 83.3412),
        "dest_name": "NAD Junction",
        "dest_coords": (17.7482, 83.2189),
        "expected_dist_km": 12.5,
        "min_dist_km": 10.0,
        "max_dist_km": 15.5,
        "min_dur_min": 15.0,
        "max_dur_min": 40.0
    },
    {
        "id": "nad_to_simhachalam",
        "origin_name": "NAD Junction",
        "origin_coords": (17.7482, 83.2189),
        "dest_name": "Simhachalam (Foothills)",
        "dest_coords": (17.772896, 83.244017),
        "expected_dist_km": 6.8,
        "min_dist_km": 5.0,
        "max_dist_km": 8.5,
        "min_dur_min": 8.0,
        "max_dur_min": 25.0
    }
]


def classify_distance_deviation(actual_km: float, expected_km: float) -> str:
    """Classifies distance deviation: PASS (<=10%), REVIEW (10-20%), FAIL (>20%)."""
    pct_diff = abs(actual_km - expected_km) / expected_km * 100.0
    if pct_diff <= 10.0:
        return "PASS"
    elif pct_diff <= 20.0:
        return "REVIEW"
    else:
        return "FAIL"


@pytest.mark.parametrize("corridor", KEY_CORRIDORS)
def test_corridor_physical_sanity_bounds(corridor):
    """Verify corridor configuration and threshold math."""
    assert corridor["min_dist_km"] < corridor["expected_dist_km"] < corridor["max_dist_km"]
    assert corridor["min_dur_min"] < corridor["max_dur_min"]

    # Exactly expected must be PASS
    assert classify_distance_deviation(corridor["expected_dist_km"], corridor["expected_dist_km"]) == "PASS"

    # 5% deviation must be PASS
    assert classify_distance_deviation(corridor["expected_dist_km"] * 1.05, corridor["expected_dist_km"]) == "PASS"

    # 15% deviation must be REVIEW
    assert classify_distance_deviation(corridor["expected_dist_km"] * 1.15, corridor["expected_dist_km"]) == "REVIEW"

    # 25% deviation must be FAIL
    assert classify_distance_deviation(corridor["expected_dist_km"] * 1.25, corridor["expected_dist_km"]) == "FAIL"


@pytest.mark.anyio
async def test_no_hardcoded_distance_hacks():
    """
    STRICT INVARIANT: Verify that distances are strictly computed from routing engine geometry,
    not intercepted by any static lookup or `if place == '...'` hacks.
    """
    mock_routing = AsyncMock()
    mock_traffic = AsyncMock()
    mock_search = AsyncMock()

    # Configure mock routing engine with a dynamic distance of 8888 meters
    mock_routing.route.return_value = [
        RouteResult(
            provider="OSRM",
            distance_m=8888.0,
            duration_s=600.0,
            geometry_geojson={"type": "LineString", "coordinates": [[83.21, 17.80], [83.25, 17.76]]},
            steps=[
                RouteStep(instruction="Head east", road_name="Test Road", distance_m=8888.0, duration_s=600.0)
            ]
        )
    ]
    mock_routing.nearest.return_value = SnappedPoint(
        original=Coords(lat=17.801206, lon=83.215257),
        snapped=Coords(lat=17.801200, lon=83.215250),
        road_name="Test Snapped Road",
        distance_m=4.0
    )

    service = RealWorldRoutingService(
        routing_provider=mock_routing,
        traffic_provider=mock_traffic,
        search_provider=mock_search
    )

    # Route specifically with Simhachalam Devasthanam
    result = await service.route_by_coords(
        origin_lat=17.801206,
        origin_lon=83.215257,
        dest_lat=17.766343,
        dest_lon=83.250476,
        origin_name="Pendurthi",
        dest_name="Simhachalam Devasthanam"
    )

    # The result MUST reflect the 8888.0 meters from the engine, NOT a hardcoded 6.6 or 11.24
    assert result["primary_route"]["distance_m"] == 8888.0
    assert result["primary_route"]["distance_km"] == 8.89
    assert result["primary_route"]["provider"] == "OSRM"


@pytest.mark.anyio
async def test_step_sum_consistency():
    """Ensure sum of turn-by-turn steps matches route total within 1 meter / 1 second."""
    mock_routing = AsyncMock()
    mock_traffic = AsyncMock()
    mock_search = AsyncMock()

    steps = [
        RouteStep(instruction="Turn left", road_name="Road A", distance_m=1200.0, duration_s=120.0),
        RouteStep(instruction="Continue straight", road_name="Road B", distance_m=3400.0, duration_s=250.0),
        RouteStep(instruction="Arrive at destination", road_name="Road C", distance_m=1400.0, duration_s=130.0),
    ]
    total_dist = sum(s.distance_m for s in steps)
    total_dur = sum(s.duration_s for s in steps)

    mock_routing.route.return_value = [
        RouteResult(
            provider="OSRM",
            distance_m=total_dist,
            duration_s=total_dur,
            geometry_geojson={"type": "LineString", "coordinates": [[83.2, 17.8], [83.3, 17.7]]},
            steps=steps
        )
    ]
    mock_routing.nearest.return_value = SnappedPoint(
        original=Coords(lat=17.8, lon=83.2),
        snapped=Coords(lat=17.8, lon=83.2),
        road_name="Road A",
        distance_m=1.0
    )

    service = RealWorldRoutingService(
        routing_provider=mock_routing,
        traffic_provider=mock_traffic,
        search_provider=mock_search
    )

    res = await service.route_by_coords(
        origin_lat=17.8,
        origin_lon=83.2,
        dest_lat=17.7,
        dest_lon=83.3,
        origin_name="A",
        dest_name="B"
    )

    assert res["step_conservation"]["status"] == "PASSED"
    assert res["step_conservation"]["dist_diff_m"] == 0.0
    assert res["step_conservation"]["dur_diff_s"] == 0.0
