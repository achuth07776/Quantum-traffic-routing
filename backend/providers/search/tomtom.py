"""
TomTom Search & Forward Geocoding Provider.

Enables dynamic, provider-backed place search and geocoding for arbitrary POIs,
addresses, junctions, beaches, hospitals, schools, and transit hubs across Visakhapatnam.
"""

import os
import logging
from urllib.parse import quote
from typing import List, Optional, Dict, Any
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PlaceSearchResult(BaseModel):
    id: str
    name: str
    address: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    category: Optional[str] = "place"
    provider: str = "TomTom"
    provider_place_id: str
    entry_points: List[Dict[str, Any]] = Field(default_factory=list, description="Candidate vehicle entry points from provider")


class TomTomSearchProvider:
    """Provider for TomTom Fuzzy Search and Forward Geocoding."""

    def __init__(self, api_key: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("TOMTOM_API_KEY", "")
        self.base_url = "https://api.tomtom.com/search/2"
        # Visakhapatnam geographic anchor
        self.default_lat = 17.72
        self.default_lon = 83.31
        self.default_radius = 50000  # 50 km search perimeter

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def search_places(
        self,
        query: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_m: int = 50000,
        limit: int = 10,
        timeout: float = 6.0
    ) -> List[PlaceSearchResult]:
        """
        Dynamically searches for places, addresses, landmarks, and businesses in Visakhapatnam.
        Never fabricates places or falls back to static hardcoded arrays.
        """
        clean_query = query.strip()
        if not clean_query or len(clean_query) < 2:
            return []

        if not self.is_configured():
            logger.warning("TomTomSearchProvider: TOMTOM_API_KEY is not configured.")
            return []

        search_lat = lat if lat is not None else self.default_lat
        search_lon = lon if lon is not None else self.default_lon

        encoded_query = quote(clean_query)
        url = f"{self.base_url}/search/{encoded_query}.json"
        params = {
            "key": self.api_key,
            "lat": search_lat,
            "lon": search_lon,
            "radius": radius_m,
            "countrySet": "IN",
            "limit": min(max(limit, 1), 20)
        }

        results: List[PlaceSearchResult] = []
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 401:
                    logger.error("TomTomSearchProvider: HTTP 401 Unauthorized (Invalid API key).")
                    return []
                if resp.status_code == 429:
                    logger.error("TomTomSearchProvider: HTTP 429 Rate Limit Exceeded.")
                    return []
                resp.raise_for_status()
                data = resp.json()

                raw_items = data.get("results", [])
                for idx, item in enumerate(raw_items):
                    pos = item.get("position", {})
                    item_lat = float(pos.get("lat", 0.0))
                    item_lon = float(pos.get("lon", 0.0))

                    if not (-90.0 <= item_lat <= 90.0 and -180.0 <= item_lon <= 180.0):
                        continue

                    poi = item.get("poi", {})
                    addr = item.get("address", {})

                    poi_name = poi.get("name")
                    freeform = addr.get("freeformAddress")

                    name = poi_name or freeform or clean_query
                    address_str = freeform or f"{name}, Visakhapatnam, Andhra Pradesh"

                    cats = poi.get("categories", [])
                    category = cats[0] if cats else item.get("type", "place")
                    place_id = str(item.get("id") or f"tt_{idx}_{item_lat}_{item_lon}")
                    raw_entries = item.get("entryPoints", [])
                    entry_points = []
                    for ep in raw_entries:
                        ep_pos = ep.get("position", {})
                        if "lat" in ep_pos and "lon" in ep_pos:
                            entry_points.append({
                                "type": ep.get("type", "main"),
                                "lat": round(float(ep_pos["lat"]), 6),
                                "lon": round(float(ep_pos["lon"]), 6)
                            })

                    results.append(
                        PlaceSearchResult(
                            id=place_id,
                            name=name,
                            address=address_str,
                            latitude=round(item_lat, 6),
                            longitude=round(item_lon, 6),
                            category=str(category),
                            provider="TomTom",
                            provider_place_id=place_id,
                            entry_points=entry_points
                        )
                    )
        except httpx.TimeoutException:
            logger.error("TomTomSearchProvider: Timeout during place search.")
            return []
        except Exception as e:
            logger.error(f"TomTomSearchProvider: Search error ({type(e).__name__}).")
            return []

        return results

    async def geocode_forward(
        self,
        query: str,
        timeout: float = 6.0
    ) -> Optional[PlaceSearchResult]:
        """Forward geocoding using TomTom Geocoding v2."""
        clean_query = query.strip()
        if not clean_query:
            return None

        if not self.is_configured():
            logger.warning("TomTomSearchProvider: TOMTOM_API_KEY is not configured.")
            return None

        encoded_query = quote(clean_query)
        url = f"{self.base_url}/geocode/{encoded_query}.json"
        params = {
            "key": self.api_key,
            "lat": self.default_lat,
            "lon": self.default_lon,
            "radius": self.default_radius,
            "countrySet": "IN",
            "limit": 1
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                raw_items = data.get("results", [])
                if not raw_items:
                    # Fall back to fuzzy search
                    fuzzy_res = await self.search_places(clean_query, limit=1, timeout=timeout)
                    return fuzzy_res[0] if fuzzy_res else None

                item = raw_items[0]
                pos = item.get("position", {})
                item_lat = float(pos.get("lat", 0.0))
                item_lon = float(pos.get("lon", 0.0))

                if not (-90.0 <= item_lat <= 90.0 and -180.0 <= item_lon <= 180.0):
                    return None

                addr = item.get("address", {})
                freeform = addr.get("freeformAddress", clean_query)
                place_id = str(item.get("id") or f"tt_geo_{item_lat}_{item_lon}")

                return PlaceSearchResult(
                    id=place_id,
                    name=freeform,
                    address=freeform,
                    latitude=round(item_lat, 6),
                    longitude=round(item_lon, 6),
                    category="address",
                    provider="TomTom",
                    provider_place_id=place_id
                )
        except Exception as e:
            logger.error(f"TomTomSearchProvider: Geocode error ({type(e).__name__}).")
            return None