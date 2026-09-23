"""
Place Resolution Service.

Resolves search results, addresses, and candidate POIs into canonical,
auditable PlaceResolution objects verified against the real road network.
"""

import logging
import math
from typing import Optional, List, Dict, Any, Tuple
from app.domain.place import PlaceResolution
from providers.routing.base import BaseRoutingProvider, Coords, SnappedPoint
from providers.search.tomtom import PlaceSearchResult, TomTomSearchProvider

logger = logging.getLogger(__name__)


class PlaceResolutionError(RuntimeError):
    """Raised when a place cannot be resolved to a valid drivable road access point."""


class PlaceResolutionService:
    """
    Authoritative place-to-road-access resolution service.
    Guarantees that routing occurs strictly from drivable access points rather
    than parcel centroids, avoiding off-road or unroutable coordinates.
    """

    def __init__(self, routing_provider: Optional[BaseRoutingProvider] = None, search_provider: Optional[TomTomSearchProvider] = None):
        self.routing_provider = routing_provider
        self.search_provider = search_provider or TomTomSearchProvider()

    def classify_confidence(self, snap_distance_m: float) -> str:
        """
        Classify snap distance into defensible confidence tiers:
        <= 50m: HIGH CONFIDENCE
        50-150m: MEDIUM CONFIDENCE
        150-500m: REVIEW (Location requires road-access confirmation)
        > 500m: INVALID FOR NORMAL DRIVING
        """
        if snap_distance_m <= 50.0:
            return "HIGH"
        elif snap_distance_m <= 150.0:
            return "MEDIUM"
        elif snap_distance_m <= 500.0:
            return "REVIEW"
        else:
            return "INVALID"

    async def resolve_place(
        self,
        name: str,
        lat: float,
        lon: float,
        address: str = "",
        category: str = "place",
        provider_place_id: str = "",
        entry_points: Optional[List[Dict[str, Any]]] = None
    ) -> PlaceResolution:
        """
        Resolves a single location into a canonical PlaceResolution object.
        Evaluates TomTom entry points first, snaps to the nearest drivable road,
        calculates snap distance, and assigns confidence tier.
        Raises PlaceResolutionError if invalid coordinates, unreachable, or > 500m.
        """
        clean_name = (name or "").strip() or "Resolved Location"
        try:
            raw_lat = float(lat)
            raw_lon = float(lon)
        except (ValueError, TypeError):
            raise PlaceResolutionError(f"Invalid coordinate format for '{clean_name}': lat={lat}, lon={lon}")

        if not (-90.0 <= raw_lat <= 90.0) or not (-180.0 <= raw_lon <= 180.0) or not math.isfinite(raw_lat) or not math.isfinite(raw_lon):
            raise PlaceResolutionError(f"Coordinates out of range for '{clean_name}': lat={raw_lat}, lon={raw_lon}")

        raw_lat = round(raw_lat, 6)
        raw_lon = round(raw_lon, 6)
        entries = entry_points or []

        if not self.routing_provider:
            raise PlaceResolutionError("Routing provider is not configured for road-access snapping.")

        # 1. Build Candidate Coordinates:
        # Prioritize vehicle entry points (main, parking, entry) then raw centroid
        candidates: List[Tuple[float, float, str]] = []

        for ep in entries:
            ep_pos = ep.get("position") if isinstance(ep.get("position"), dict) else {}
            ep_lat = ep.get("lat", ep_pos.get("lat"))
            ep_lon = ep.get("lon", ep_pos.get("lon"))
            ep_type = ep.get("type", "main")
            if ep_lat is not None and ep_lon is not None:
                try:
                    c_lat = float(ep_lat)
                    c_lon = float(ep_lon)
                    if -90.0 <= c_lat <= 90.0 and -180.0 <= c_lon <= 180.0:
                        candidates.append((c_lat, c_lon, f"TOMTOM_ENTRY_POINT_{str(ep_type).upper()}"))
                except (ValueError, TypeError):
                    continue

        # Candidate: raw POI centroid
        candidates.append((raw_lat, raw_lon, "OSRM_NEAREST_CENTROID"))

        # 2. Evaluate candidates via OSRM /nearest snapping
        best_candidate: Optional[SnappedPoint] = None
        best_method = "OSRM_NEAREST"
        min_snap_distance = float("inf")

        for cand_lat, cand_lon, method in candidates:
            try:
                snapped: Optional[SnappedPoint] = await self.routing_provider.nearest(Coords(lat=cand_lat, lon=cand_lon))
                # Accept candidate if it successfully snapped and is closer to a drivable road
                if snapped and snapped.distance_m < min_snap_distance:
                    min_snap_distance = snapped.distance_m
                    best_candidate = snapped
                    best_method = method
            except Exception as e:
                logger.warning(f"Error snapping candidate ({cand_lat}, {cand_lon}): {e}")

        # 3. Strict failure semantics
        if best_candidate is None or best_candidate.snapped is None:
            raise PlaceResolutionError(f"Unable to determine a drivable access point for '{clean_name}'.")

        snap_dist = round(float(best_candidate.distance_m), 2)
        if snap_dist > 500.0:
            raise PlaceResolutionError(f"'{clean_name}' is {snap_dist:.0f} m from the nearest drivable road.")

        access_lat = round(best_candidate.snapped.lat, 6)
        access_lon = round(best_candidate.snapped.lon, 6)
        road_name = (best_candidate.road_name or "").strip() or "Unnamed road"
        confidence = self.classify_confidence(snap_dist)

        return PlaceResolution(
            provider="TomTom",
            provider_place_id=provider_place_id or f"tt_{raw_lat}_{raw_lon}",
            name=clean_name,
            address=address or clean_name,
            category=category or "place",
            latitude=raw_lat,
            longitude=raw_lon,
            access_latitude=access_lat,
            access_longitude=access_lon,
            access_road_name=road_name,
            snap_distance_m=snap_dist,
            resolution_method=best_method,
            confidence=confidence,
            entry_points_available=len(entries)
        )

    async def resolve_from_search_result(self, place: PlaceSearchResult) -> PlaceResolution:
        """Convenience method to resolve directly from PlaceSearchResult."""
        return await self.resolve_place(
            name=place.name,
            lat=place.latitude,
            lon=place.longitude,
            address=place.address,
            category=place.category or "place",
            provider_place_id=place.provider_place_id or place.id,
            entry_points=place.entry_points
        )
