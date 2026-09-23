"""
Unit and Integration Tests for TomTom Traffic Flow and Incidents Provider.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from providers.traffic.tomtom import TomTomTrafficProvider, TomTomFlowSegment
from providers.traffic.base import IncidentReport


def test_tomtom_traffic_initialization():
    provider = TomTomTrafficProvider(api_key="test_key")
    assert provider.is_configured() is True
    assert provider.api_key == "test_key"

    unconfigured = TomTomTrafficProvider(api_key="")
    assert unconfigured.is_configured() is False


@pytest.mark.anyio
async def test_get_flow_segment_mock():
    provider = TomTomTrafficProvider(api_key="test_key")

    mock_resp_data = {
        "flowSegmentData": {
            "currentSpeed": 38.0,
            "freeFlowSpeed": 50.0,
            "currentTravelTime": 120,
            "freeFlowTravelTime": 90,
            "confidence": 0.92,
            "roadClosure": False,
            "coordinates": {
                "coordinate": [
                    {"latitude": 17.7144, "longitude": 83.3341},
                    {"latitude": 17.7150, "longitude": 83.3350}
                ]
            }
        }
    }

    mock_resp = httpx.Response(200, json=mock_resp_data, request=httpx.Request("GET", "http://test"))

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
        segment = await provider.get_flow_segment(17.7144, 83.3341)
        assert segment is not None
        assert segment.current_speed_kmh == 38.0
        assert segment.free_flow_speed_kmh == 50.0
        assert segment.confidence == 0.92
        assert segment.road_closure is False
        assert len(segment.coordinates) == 2


@pytest.mark.anyio
async def test_get_flow_segment_road_closure():
    provider = TomTomTrafficProvider(api_key="test_key")

    mock_resp_data = {
        "flowSegmentData": {
            "currentSpeed": 0.0,
            "freeFlowSpeed": 60.0,
            "currentTravelTime": 9999,
            "freeFlowTravelTime": 60,
            "confidence": 0.99,
            "roadClosure": True,
            "coordinates": {"coordinate": []}
        }
    }

    mock_resp = httpx.Response(200, json=mock_resp_data, request=httpx.Request("GET", "http://test"))

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
        segment = await provider.get_flow_segment(17.7348, 83.3245)
        assert segment is not None
        assert segment.road_closure is True
        assert segment.current_speed_kmh == 0.0


@pytest.mark.anyio
async def test_get_incidents_mock():
    provider = TomTomTrafficProvider(api_key="test_key")

    mock_resp_data = {
        "incidents": [
            {
                "id": "inc_999",
                "geometry": {
                    "type": "Point",
                    "coordinates": [83.3245, 17.7348]
                },
                "properties": {
                    "iconCategory": 8,  # Road Closed
                    "events": [
                        {"description": "Road closed due to bridge maintenance"}
                    ],
                    "startTime": "2026-09-04T10:00:00Z",
                    "endTime": "2026-09-04T18:00:00Z"
                }
            },
            {
                "id": "inc_888",
                "geometry": {
                    "type": "Point",
                    "coordinates": [83.3005, 17.7118]
                },
                "properties": {
                    "iconCategory": 1,  # Accident
                    "events": [
                        {"description": "Minor vehicle collision causing slow traffic"}
                    ],
                    "startTime": "2026-09-04T11:00:00Z"
                }
            }
        ]
    }

    mock_resp = httpx.Response(200, json=mock_resp_data, request=httpx.Request("GET", "http://test"))

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
        incidents = await provider.get_incidents((83.1, 17.6, 83.4, 17.9))
        assert len(incidents) == 2

        assert incidents[0].incident_id.startswith("tt_inc_") or incidents[0].incident_id == "inc_999"
        assert incidents[0].type == "ROAD_CLOSURE"
        assert incidents[0].severity == "CRITICAL"
        assert incidents[0].lat == 17.7348
        assert incidents[0].lon == 83.3245
        assert "bridge maintenance" in incidents[0].description

        assert incidents[1].incident_id.startswith("tt_inc_") or incidents[1].incident_id == "inc_888"
        assert incidents[1].type in ["ACCIDENT", "CONGESTION"]
        assert incidents[1].severity in ["HIGH", "MEDIUM"]
        assert incidents[1].lat == 17.7118
        assert incidents[1].lon == 83.3005


@pytest.mark.anyio
async def test_get_flow_uncredentialed():
    provider = TomTomTrafficProvider(api_key="")
    snapshot = await provider.get_flow()
    assert snapshot.source_status == "UNAVAILABLE"
    assert snapshot.segments_updated == 0
    assert snapshot.observations == []


@pytest.mark.anyio
async def test_traffic_api_error_handling():
    provider = TomTomTrafficProvider(api_key="test_key")

    mock_resp = httpx.Response(500, text="Internal Server Error", request=httpx.Request("GET", "http://test"))

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
        segment = await provider.get_flow_segment(17.7144, 83.3341)
        assert segment is None

        incidents = await provider.get_incidents((83.1, 17.6, 83.4, 17.9))
        assert incidents == []


@pytest.mark.anyio
async def test_live_tomtom_traffic_if_credentialed():
    api_key = os.environ.get("TOMTOM_API_KEY")
    if not api_key:
        pytest.skip("TOMTOM_API_KEY not configured; skipping live traffic test.")

    provider = TomTomTrafficProvider(api_key=api_key)
    # Check flow at RK Beach
    segment = await provider.get_flow_segment(17.7144, 83.3341)
    if segment:
        assert segment.free_flow_speed_kmh > 0
        assert segment.current_speed_kmh >= 0
        assert 0.0 <= segment.confidence <= 1.0
