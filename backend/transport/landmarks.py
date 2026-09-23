"""Visakhapatnam landmark registry."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Landmark(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    category: str
    entry_points: Optional[List[Dict[str, Any]]] = None

class LandmarkRegistry:
    def __init__(self):
        self._landmarks = [
            Landmark(id="rk_beach", name="RK Beach / Submarine Museum", lat=17.7144, lon=83.3341, category="beach"),
            Landmark(id="kailasagiri_hill", name="Kailasagiri Hill", lat=17.7540, lon=83.3724, category="tourist", entry_points=[{"type": "main", "lat": 17.7490, "lon": 83.3420}]),
            Landmark(id="rushikonda_beach", name="Rushikonda Beach / IT SEZ", lat=17.7818, lon=83.3854, category="beach"),
            Landmark(id="simhachalam_temple", name="Simhachalam Temple", lat=17.7685, lon=83.2421, category="tourist"),
            Landmark(id="visakhapatnam_railway_station", name="Visakhapatnam Railway Station", lat=17.7214, lon=83.2981, category="transit"),
            Landmark(id="nad_junction", name="NAD Junction", lat=17.7482, lon=83.2189, category="junction"),
            Landmark(id="gajuwaka_junction", name="Gajuwaka Junction", lat=17.6896, lon=83.2128, category="junction"),
            Landmark(id="maddilapalem_junction", name="Maddilapalem Junction", lat=17.7348, lon=83.3245, category="junction"),
            Landmark(id="jagadamba_junction", name="Jagadamba Junction", lat=17.7118, lon=83.3005, category="junction"),
            Landmark(id="mvp_colony", name="MVP Colony", lat=17.7441, lon=83.3412, category="residential"),
            Landmark(id="siripuram_junction", name="Siripuram Junction", lat=17.7226, lon=83.3156, category="junction"),
            Landmark(id="dwaraka_bus_station", name="Dwaraka Bus Station", lat=17.7130, lon=83.2960, category="transit"),
            Landmark(id="visakhapatnam_port", name="Visakhapatnam Port", lat=17.6975, lon=83.2842, category="port"),
            Landmark(id="steel_plant_main_gate", name="Steel Plant Main Gate", lat=17.6415, lon=83.1610, category="industrial"),
            Landmark(id="scindia_junction", name="Scindia Junction / Shipyard", lat=17.6745, lon=83.2655, category="industrial"),
            Landmark(id="pendurthi", name="Pendurthi", lat=17.8012, lon=83.2153, category="residential"),
            Landmark(id="madhurawada", name="Madhurawada", lat=17.7890, lon=83.3560, category="residential"),
            Landmark(id="asilmetta_junction", name="Asilmetta Junction", lat=17.7195, lon=83.3105, category="junction"),
            Landmark(id="waltair_uplands", name="Waltair Uplands", lat=17.7265, lon=83.3235, category="residential"),
            Landmark(id="gitam_university", name="GITAM University", lat=17.7639, lon=83.3780, category="education", entry_points=[{"type": "main", "lat": 17.7800, "lon": 83.3800}]),
            Landmark(id="andhra_university", name="Andhra University", lat=17.7300, lon=83.3190, category="education"),
            Landmark(id="king_george_hospital", name="King George Hospital", lat=17.7180, lon=83.3060, category="medical"),
            Landmark(id="vims", name="Visakha Institute of Medical Sciences (VIMS)", lat=17.7520, lon=83.3130, category="medical"),
            Landmark(id="poorna_market", name="Poorna Market", lat=17.7050, lon=83.2930, category="commercial"),
            Landmark(id="kancharapalem", name="Kancharapalem", lat=17.7380, lon=83.2850, category="residential"),
            Landmark(id="cmr_central_mall", name="CMR Central Mall", lat=17.7410, lon=83.3230, category="commercial"),
            Landmark(id="marripalem_vuda_park", name="Marripalem VUDA Park", lat=17.7560, lon=83.3450, category="tourist"),
            Landmark(id="bheemili_beach", name="Bheemili Beach", lat=17.8900, lon=83.4520, category="beach"),
        ]

    def get_all(self) -> List[Landmark]:
        return self._landmarks

    def get_by_id(self, id: str) -> Optional[Landmark]:
        for lm in self._landmarks:
            if lm.id == id:
                return lm
        return None

    def search(self, query: str) -> List[Landmark]:
        q = query.lower()
        return [lm for lm in self._landmarks if q in lm.name.lower()]

    def get_default_origin(self) -> Landmark:
        return self.get_by_id("rk_beach") # type: ignore

    def get_default_destination(self) -> Landmark:
        return self.get_by_id("rushikonda_beach") # type: ignore

    def get_default_depot(self) -> Landmark:
        return self.get_by_id("maddilapalem_junction") # type: ignore
