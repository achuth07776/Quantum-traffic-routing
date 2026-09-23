"""
Curated Geocoding and Road Snapping Service for Greater Visakhapatnam.

Complies with OpenStreetMap usage policy by utilizing local indexed geocoding
with caching and delegating road-network snapping directly to OSRM /nearest.
"""

from typing import List, Dict, Any, Optional, Tuple
from providers.routing.base import BaseRoutingProvider, Coords


class GeocodedPlace:
    def __init__(
        self,
        place_id: str,
        name: str,
        category: str,
        lat: float,
        lon: float,
        aliases: List[str]
    ):
        self.place_id = place_id
        self.name = name
        self.category = category
        self.lat = lat
        self.lon = lon
        self.aliases = [a.lower() for a in aliases]

    def matches(self, query_tokens: List[str]) -> bool:
        searchable_text = f"{self.name.lower()} {self.category.lower()} {' '.join(self.aliases)}"
        return all(token in searchable_text for token in query_tokens)


def classify_snap_quality(distance_m: float, road_name: str = "") -> Tuple[str, Optional[str]]:
    """
    Evaluates snap distance according to application quality thresholds:
      <= 50 m: GOOD
      50 - 200 m: ACCEPTABLE
      200 - 500 m: WARNING
      > 500 m: REVIEW_LOCATION
    """
    rd = f" ({road_name})" if road_name else ""
    if distance_m <= 50.0:
        return ("GOOD", None)
    elif distance_m <= 200.0:
        return ("ACCEPTABLE", None)
    elif distance_m <= 500.0:
        return ("WARNING", f"Location is {round(distance_m)}m from nearest drivable road{rd}.")
    else:
        dist_str = f"{round(distance_m / 1000.0, 2)} km" if distance_m >= 1000 else f"{round(distance_m)}m"
        return ("REVIEW_LOCATION", f"[!] Location snapped {dist_str} to nearest drivable road{rd}.")


class VizagGeocodingService:
    """
    Self-contained geocoding service for Visakhapatnam.
    Prevents unauthorized rate-limit violations on public Nominatim endpoints.
    """

    def __init__(self):
        self._places: List[GeocodedPlace] = []
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._init_database()

    def _init_database(self):
        entries = [
            ("rk_beach", "Ramakrishna Beach (RK Beach)", "beach", 17.7144, 83.3341, ["rk beach", "submarine museum", "beach road", "dr ntr beach road", "ins kursura"]),
            ("rushikonda_beach", "Rushikonda Beach & IT SEZ", "beach", 17.7818, 83.3854, ["rushikonda", "it park", "tech park", "vizag it hub", "radisson"]),
            ("kailasagiri", "Kailasagiri Hilltop Park", "tourist", 17.7540, 83.3724, ["kailasagiri", "ropeway", "shiva parvati statue", "hilltop"]),
            ("simhachalam", "Simhachalam Temple", "spiritual", 17.7685, 83.2421, ["simhachalam", "varaha lakshmi narasimha", "temple hill"]),
            ("vizag_railway_station", "Visakhapatnam Railway Station", "transit", 17.7214, 83.2981, ["railway station", "vizag station", "vskp", "central station"]),
            ("nad_junction", "NAD Junction Flyover", "junction", 17.7482, 83.2189, ["nad", "nad flyover", "airport road junction", "gopalapatnam road"]),
            ("gajuwaka_junction", "Gajuwaka Industrial Hub", "junction", 17.6896, 83.2128, ["gajuwaka", "industrial zone", "bhel junction", "autonagar"]),
            ("maddilapalem_junction", "Maddilapalem RTC Bus Complex", "junction", 17.7348, 83.3245, ["maddilapalem", "rtc bus complex", "national highway junction"]),
            ("jagadamba_junction", "Jagadamba Center", "commercial", 17.7118, 83.3005, ["jagadamba", "jagadamba theatre", "shopping center", "daba gardens"]),
            ("mvp_colony", "MVP Colony Sector 1-12", "residential", 17.7441, 83.3412, ["mvp", "mvp colony", "as raja ground", "sector 3", "sector 7"]),
            ("siripuram_junction", "Siripuram Circle (VUDA)", "junction", 17.7226, 83.3156, ["siripuram", "vuda office", "gurajada kalakshetram", "dutt island"]),
            ("dwaraka_bus_station", "Dwaraka Bus Station (RTC Complex)", "transit", 17.7130, 83.2960, ["rtc complex", "dbs", "central bus stand"]),
            ("visakhapatnam_port", "Visakhapatnam Sea Port & Dockyard", "port", 17.6975, 83.2842, ["port", "harbour", "dockyard", "outer harbour", "concor"]),
            ("steel_plant", "Visakhapatnam Steel Plant (RINL)", "industrial", 17.6415, 83.1610, ["steel plant", "rinl", "ukkunagaram", "kurmannapalem"]),
            ("scindia_junction", "Scindia Junction (Shipyard)", "junction", 17.6745, 83.2655, ["scindia", "hindustan shipyard", "naval dockyard gate"]),
            ("pendurthi", "Pendurthi Junction", "transit", 17.8285, 83.1995, ["pendurthi", "aravalli link", "sh-9"]),
            ("madhurawada", "Madhurawada Cricket Stadium", "residential", 17.7890, 83.3560, ["madhurawada", "aca vdca cricket stadium", "car shed junction", "pm palem"]),
            ("andhra_university", "Andhra University North Campus", "education", 17.7300, 83.3190, ["au", "andhra university", "au engineering", "sir c r reddy"]),
            ("gitam_university", "GITAM Deemed University", "education", 17.7639, 83.3780, ["gitam", "gitam college", "rushikonda campus"]),
            ("kgh_hospital", "King George Hospital (KGH)", "medical", 17.7180, 83.3060, ["kgh", "king george hospital", "medical college", "maharani peta"]),
            ("vims_hospital", "VIMS Super Specialty Hospital", "medical", 17.7520, 83.3130, ["vims", "visakha institute of medical sciences", "hanumanthawaka"]),
            ("cmr_central", "CMR Central Mall (Maddilapalem)", "commercial", 17.7410, 83.3230, ["cmr central", "inox", "mall", "shopping"]),
            ("bheemili_beach", "Bheemunipatnam (Bheemili Beach)", "tourist", 17.8900, 83.4520, ["bheemili", "dutch cemetery", "light house", "beach"]),
            ("yarada_beach", "Yarada Beach & Dolphin's Nose", "tourist", 17.6540, 83.2690, ["yarada", "dolphins nose", "light house"]),
            ("lawson_bay", "Lawson's Bay Colony", "beach", 17.7348, 83.3450, ["lawsons bay", "shanti ashram", "beach"]),
            ("seethammadhara", "Seethammadhara North Extension", "residential", 17.7430, 83.3110, ["seethammadhara", "hb colony", "satyam junction"]),
            ("marripalem", "Marripalem VUDA Layout", "residential", 17.7560, 83.2640, ["marripalem", "vuda park", "railway quarters"]),
            ("kancharapalem", "Kancharapalem Railway Bridge", "transit", 17.7380, 83.2850, ["kancharapalem", "urvasi junction", "railway flyover"]),
            ("kurmannapalem", "Kurmannapalem Steel Plant Gate", "junction", 17.6520, 83.1530, ["kurmannapalem", "duvvada road", "highway toll"]),
            ("duvvada_railway_station", "Duvvada Satellite Railway Station", "transit", 17.6980, 83.1560, ["duvvada", "duvvada station", "vseb"])
        ]
        for pid, name, cat, lat, lon, aliases in entries:
            self._places.append(GeocodedPlace(pid, name, cat, lat, lon, aliases))

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        clean_query = query.strip().lower()
        if not clean_query:
            return []

        if clean_query in self._cache:
            return self._cache[clean_query][:limit]

        tokens = clean_query.split()
        matches = []
        for place in self._places:
            if place.matches(tokens):
                matches.append({
                    "place_id": place.place_id,
                    "name": place.name,
                    "category": place.category,
                    "lat": place.lat,
                    "lon": place.lon,
                    "display_name": f"{place.name}, Visakhapatnam, Andhra Pradesh"
                })

        # Cache results for policy compliance
        self._cache[clean_query] = matches
        return matches[:limit]

    async def geocode_and_snap(
        self,
        query: str,
        routing_provider: BaseRoutingProvider
    ) -> Optional[Dict[str, Any]]:
        """
        Resolves location query to coordinates, then calls OSRM /nearest
        to snap to the nearest legal road segment with road name and distance.
        Enforces snap quality classification and warnings.
        """
        matches = self.search(query, limit=1)
        if not matches:
            return None

        best = matches[0]
        coord = Coords(lat=best["lat"], lon=best["lon"])

        snapped = await routing_provider.nearest(coord)
        road_name = snapped.road_name or "Highway / Arterial Segment"
        snap_quality, snap_warning = classify_snap_quality(snapped.distance_m, road_name)

        return {
            "query": query,
            "place_name": best["name"],
            "category": best["category"],
            "original_coords": {"lat": best["lat"], "lon": best["lon"]},
            "snapped_road": {
                "road_name": road_name,
                "lat": snapped.snapped.lat,
                "lon": snapped.snapped.lon,
                "snap_distance_m": round(snapped.distance_m, 1),
                "snap_quality": snap_quality,
                "snap_warning": snap_warning
            }
        }
