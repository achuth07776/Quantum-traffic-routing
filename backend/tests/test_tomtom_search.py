"""
Unit and Integration Tests for TomTom Search and Geocoding Provider.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from providers.search.tomtom import TomTomSearchProvider, PlaceSearchResult


def test_tomtom_search_initialization():
    provider = TomTomSearchProvider(api_key="test_key")
    assert provider.is_configured() is True
    assert provider.api_key == "test_key"

    unconfigured = TomTomSearchProvider(api_key="")
    assert unconfigured.is_configured() is False


@pytest.mark.anyio
async def test_search_places_empty_query():
    provider = TomTomSearchProvider(api_key="test_key")
    results = await provider.search_places("")
    assert results == []

    results_whitespace = await provider.search_places("   ")
    assert results_whitespace == []


@pytest.mark.anyio
async def test_search_places_mock_parsing():
    provider = TomTomSearchProvider(api_key="test_key")

    mock_response_data = {
        "results": [
            {
                "id": "poi_123",
                "poi": {
                    "name": "RK Beach Submarine Museum",
                    "classifications": [{"code": "MUSEUM"}]
                },
                "address": {
                    "freeformAddress": "RK Beach Road, Pandurangapuram, Visakhapatnam 530003"
                },
                "position": {
                    "lat": 17.7144,
                    "lon": 83.3341
                },
                "dist": 1200.5
            },
            {
                "id": "poi_456",
                "poi": {
                    "name": "Novotel Visakhapatnam Varun Beach"
                },
                "address": {
                    "freeformAddress": "Dr NTR Beach Rd, Krishna Nagar, Visakhapatnam 530002"
                },
                "position": {
                    "lat": 17.7121,
                    "lon": 83.3195
                }
            }
        ]
    }

    mock_resp = httpx.Response(200, json=mock_response_data, request=httpx.Request("GET", "http://test"))

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
        places = await provider.search_places("Beach", limit=5)
        assert len(places) == 2
        assert places[0].name == "RK Beach Submarine Museum"
        assert places[0].latitude == 17.7144
        assert places[0].longitude == 83.3341
        assert places[0].category in ["place", "MUSEUM"]
        assert places[0].address == "RK Beach Road, Pandurangapuram, Visakhapatnam 530003"

        assert places[1].name == "Novotel Visakhapatnam Varun Beach"
        assert places[1].latitude == 17.7121
        assert places[1].longitude == 83.3195
        assert places[1].category == "place"


@pytest.mark.anyio
async def test_geocode_forward_mock():
    provider = TomTomSearchProvider(api_key="test_key")

    mock_response_data = {
        "results": [
            {
                "id": "geo_789",
                "poi": {"name": "Rushikonda Beach"},
                "address": {"freeformAddress": "Rushikonda, Visakhapatnam"},
                "position": {"lat": 17.7818, "lon": 83.3854}
            }
        ]
    }

    mock_resp = httpx.Response(200, json=mock_response_data, request=httpx.Request("GET", "http://test"))

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
        place = await provider.geocode_forward("Rushikonda")
        assert place is not None
        assert place.name in ["Rushikonda Beach", "Rushikonda, Visakhapatnam"]
        assert place.latitude == 17.7818
        assert place.longitude == 83.3854


@pytest.mark.anyio
async def test_search_places_error_handling():
    provider = TomTomSearchProvider(api_key="test_key")

    mock_resp = httpx.Response(429, text="Rate limit exceeded", request=httpx.Request("GET", "http://test"))

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
        places = await provider.search_places("Vizag")
        assert places == []


@pytest.mark.anyio
async def test_search_places_network_exception():
    provider = TomTomSearchProvider(api_key="test_key")

    with patch.object(httpx.AsyncClient, "get", side_effect=httpx.ConnectError("Network timeout")):
        places = await provider.search_places("Vizag")
        assert places == []


@pytest.mark.anyio
async def test_live_tomtom_search_if_credentialed():
    api_key = os.environ.get("TOMTOM_API_KEY")
    if not api_key:
        pytest.skip("TOMTOM_API_KEY not configured; skipping live search test.")

    provider = TomTomSearchProvider(api_key=api_key)
    places = await provider.search_places("Novotel", limit=5)
    assert len(places) > 0
    assert any("novotel" in p.name.lower() for p in places)
