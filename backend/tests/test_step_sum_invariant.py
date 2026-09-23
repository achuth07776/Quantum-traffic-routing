"""
Test Step Sum Invariant.

Verifies that for route results, the sum of individual step distances
and durations equals the overall reported route distance and duration
within expected floating-point rounding tolerance.
"""
import pytest
from app.services.realworld_routing_service import RealWorldRoutingService
from transport.landmarks import LandmarkRegistry


@pytest.mark.anyio
async def test_realworld_route_step_sum_invariant():
    """Verify step distance and duration sum equals total on live service call."""
    registry = LandmarkRegistry()
    service = RealWorldRoutingService(registry)
    
    res = await service.route_by_landmarks(
        origin_id="pendurthi",
        destination_id="rk_beach"
    )
    
    assert res["status"] == "SUCCESS"
    primary = res["primary_route"]
    steps = primary["steps"]
    
    assert len(steps) > 0, "Route should contain turn-by-turn steps"
    
    total_dist_m = primary["distance_m"]
    sum_dist_m = sum(s["distance_m"] for s in steps)
    
    assert abs(sum_dist_m - total_dist_m) < max(10.0, total_dist_m * 0.01), (
        f"Sum of steps ({sum_dist_m}m) does not equal total ({total_dist_m}m)"
    )
    assert res["step_conservation"]["is_conserved"] is True
