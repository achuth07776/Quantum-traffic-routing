"""
Unit and Integration tests for PlaceResolutionService.
Validates candidate entry point evaluation, OSRM /nearest snapping,
and confidence classification tiers (HIGH <= 50m, MEDIUM 50-150m, REVIEW 150-500m, INVALID > 500m).
"""

import pytest
from unittest.mock import AsyncMock
from app.services.place_resolution_service import PlaceResolutionService, PlaceResolutionError
from providers.routing.base import SnappedPoint, Coords


@pytest.fixture
def mock_routing_provider():
    provider = AsyncMock()
    return provider


@pytest.mark.anyio
async def test_resolve_place_high_confidence(mock_routing_provider):
    """Test place snapping within 50m gets classified as HIGH confidence."""
    mock_routing_provider.nearest.return_value = SnappedPoint(
        original=Coords(lat=17.801206, lon=83.215257),
        snapped=Coords(lat=17.801202, lon=83.215290),
        road_name="Pendurthi Road",
        distance_m=3.53
    )

    resolver = PlaceResolutionService(routing_provider=mock_routing_provider)
    res = await resolver.resolve_place(
        name="Pendurthi",
        lat=17.801206,
        lon=83.215257
    )

    assert res.name == "Pendurthi"
    assert res.confidence == "HIGH"
    assert res.snap_distance_m == 3.53
    assert res.access_road_name == "Pendurthi Road"
    assert res.access_latitude == 17.801202
    assert res.access_longitude == 83.215290
    assert res.resolution_method == "OSRM_NEAREST_CENTROID"


@pytest.mark.anyio
async def test_resolve_place_medium_confidence(mock_routing_provider):
    """Test place snapping between 50m and 150m gets classified as MEDIUM confidence."""
    mock_routing_provider.nearest.return_value = SnappedPoint(
        original=Coords(lat=17.766343, lon=83.250476),
        snapped=Coords(lat=17.765868, lon=83.250482),
        road_name="Simhachalam Temple Ghat Road",
        distance_m=52.58
    )

    resolver = PlaceResolutionService(routing_provider=mock_routing_provider)
    res = await resolver.resolve_place(
        name="Simhachalam Devasthanam",
        lat=17.766343,
        lon=83.250476
    )

    assert res.name == "Simhachalam Devasthanam"
    assert res.confidence == "MEDIUM"
    assert res.snap_distance_m == 52.58
    assert res.access_road_name == "Simhachalam Temple Ghat Road"


@pytest.mark.anyio
async def test_resolve_place_review_confidence(mock_routing_provider):
    """Test place snapping between 150m and 500m gets classified as REVIEW confidence."""
    mock_routing_provider.nearest.return_value = SnappedPoint(
        original=Coords(lat=17.7200, lon=83.3100),
        snapped=Coords(lat=17.7220, lon=83.3115),
        road_name="Beach Access Road",
        distance_m=280.0
    )

    resolver = PlaceResolutionService(routing_provider=mock_routing_provider)
    res = await resolver.resolve_place(
        name="Off-road Park",
        lat=17.7200,
        lon=83.3100
    )

    assert res.confidence == "REVIEW"
    assert res.snap_distance_m == 280.0


@pytest.mark.anyio
async def test_resolve_place_invalid_confidence(mock_routing_provider):
    """Test place snapping > 500m raises PlaceResolutionError."""
    mock_routing_provider.nearest.return_value = SnappedPoint(
        original=Coords(lat=17.7540, lon=83.3724),
        snapped=Coords(lat=17.7500, lon=83.3600),
        road_name="Beach Road",
        distance_m=1250.0
    )

    resolver = PlaceResolutionService(routing_provider=mock_routing_provider)
    with pytest.raises(PlaceResolutionError) as exc_info:
        await resolver.resolve_place(
            name="Kailasagiri Peak",
            lat=17.7540,
            lon=83.3724
        )
    assert "1250 m" in str(exc_info.value) or "drivable road" in str(exc_info.value)


@pytest.mark.anyio
async def test_resolve_place_with_candidate_entry_points(mock_routing_provider):
    """Test that resolver evaluates entry points and picks the closest drivable access point."""
    async def mock_nearest(coords):
        if abs(coords.lat - 17.750) < 0.001:
            return SnappedPoint(original=coords, snapped=Coords(lat=17.752, lon=83.250), road_name="Outer Road", distance_m=220.0)
        elif abs(coords.lat - 17.755) < 0.001:
            return SnappedPoint(original=coords, snapped=Coords(lat=17.7551, lon=83.2551), road_name="Main Gate Road", distance_m=11.5)
        else:
            return SnappedPoint(original=coords, snapped=Coords(lat=17.756, lon=83.256), road_name="Parking Road", distance_m=45.0)

    mock_routing_provider.nearest.side_effect = mock_nearest

    entry_points = [
        {"type": "main", "position": {"lat": 17.755, "lon": 83.255}},
        {"type": "parking", "position": {"lat": 17.756, "lon": 83.256}}
    ]

    resolver = PlaceResolutionService(routing_provider=mock_routing_provider)
    res = await resolver.resolve_place(
        name="Major Landmark Complex",
        lat=17.750,
        lon=83.250,
        entry_points=entry_points
    )

    assert res.confidence == "HIGH"
    assert res.snap_distance_m == 11.5
    assert res.access_road_name == "Main Gate Road"
    assert res.resolution_method == "TOMTOM_ENTRY_POINT_MAIN"
    assert res.entry_points_available == 2


@pytest.mark.anyio
async def test_resolve_place_without_routing_provider():
    """Test place resolution raises PlaceResolutionError when no routing provider is available."""
    resolver = PlaceResolutionService(routing_provider=None)
    with pytest.raises(PlaceResolutionError) as exc_info:
        await resolver.resolve_place(
            name="Test Place",
            lat=17.700,
            lon=83.300
        )
    assert "Routing provider" in str(exc_info.value)
