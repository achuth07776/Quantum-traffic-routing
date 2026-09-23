import math
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple
from app.domain.bpr import calculate_bpr_travel_time, calculate_edge_emissions, calculate_composite_cost

class RoadGraph:
    """
    Transportation Network Graph wrapping networkx.DiGraph with physical spatial attributes,
    dynamic BPR congestion models, and incident injection capabilities.
    """
    def __init__(self, graph_id: str = "urban_network"):
        self.graph_id = graph_id
        self.graph = nx.DiGraph()
        
    def add_node(self, node_id: str, lat: float, lon: float, name: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        self.graph.add_node(
            str(node_id),
            lat=float(lat),
            lon=float(lon),
            name=name or str(node_id),
            metadata=metadata or {}
        )
        
    def add_edge(
        self,
        u: str,
        v: str,
        length_km: float,
        free_flow_speed_kmh: float = 50.0,
        capacity_vph: float = 1500.0,
        current_flow_vph: float = 500.0,
        road_type: str = "primary",
        is_closed: bool = False,
        incident_multiplier: float = 1.0,
        geometry: Optional[List[List[float]]] = None,
        name: str = ""
    ) -> None:
        u_str, v_str = str(u), str(v)
        self.graph.add_edge(
            u_str,
            v_str,
            length_km=float(length_km),
            free_flow_speed_kmh=float(free_flow_speed_kmh),
            capacity_vph=float(capacity_vph),
            current_flow_vph=float(current_flow_vph),
            base_flow_vph=float(current_flow_vph),
            road_type=road_type,
            is_closed=bool(is_closed),
            incident_multiplier=float(incident_multiplier),
            geometry=geometry or [],
            name=name or f"{u_str}->{v_str}"
        )
        
    @property
    def nodes(self):
        return self.graph.nodes
        
    @property
    def edges(self):
        return self.graph.edges

    def get_node_coords(self, node_id: str) -> Tuple[float, float]:
        node = self.graph.nodes[str(node_id)]
        return node["lat"], node["lon"]

    def get_neighbors(self, node_id: str) -> List[str]:
        return list(self.graph.successors(str(node_id)))

    def update_incident(self, u: str, v: str, incident_multiplier: float = 1.0, is_closed: bool = False) -> bool:
        u_str, v_str = str(u), str(v)
        if self.graph.has_edge(u_str, v_str):
            self.graph[u_str][v_str]["incident_multiplier"] = float(incident_multiplier)
            self.graph[u_str][v_str]["is_closed"] = bool(is_closed)
            return True
        return False

    def reset_incidents(self) -> None:
        for u, v, data in self.graph.edges(data=True):
            data["incident_multiplier"] = 1.0
            data["is_closed"] = False
            data["current_flow_vph"] = data.get("base_flow_vph", data["capacity_vph"] * 0.4)

    def get_edge_metrics(self, u: str, v: str, weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        data = self.graph[str(u)][str(v)]
        is_closed = data.get("is_closed", False)
        length_km = data.get("length_km", 1.0)
        speed = data.get("free_flow_speed_kmh", 50.0)
        flow = data.get("current_flow_vph", 500.0)
        capacity = data.get("capacity_vph", 1500.0)
        inc_mult = data.get("incident_multiplier", 1.0)
        
        if is_closed:
            return {
                "travel_time_min": float('inf'),
                "distance_km": length_km,
                "emissions_g": float('inf'),
                "cost": float('inf'),
                "is_closed": True
            }
            
        travel_time = calculate_bpr_travel_time(
            length_km=length_km,
            free_flow_speed_kmh=speed,
            flow_vph=flow,
            capacity_vph=capacity,
            incident_multiplier=inc_mult
        )
        
        emissions = calculate_edge_emissions(
            length_km=length_km,
            travel_time_min=travel_time,
            free_flow_speed_kmh=speed
        )
        
        cost = calculate_composite_cost(
            length_km=length_km,
            travel_time_min=travel_time,
            flow_vph=flow,
            capacity_vph=capacity,
            emissions_g=emissions,
            weights=weights,
            is_closed=is_closed
        )
        
        return {
            "travel_time_min": travel_time,
            "distance_km": length_km,
            "emissions_g": emissions,
            "cost": cost,
            "is_closed": False
        }

    def get_path_metrics(self, path: List[str], weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        if not path or len(path) < 2:
            return {
                "distance_km": 0.0,
                "travel_time_min": float('inf'),
                "cost": float('inf'),
                "emissions_g": float('inf'),
                "is_feasible": False
            }
            
        total_dist = 0.0
        total_time = 0.0
        total_cost = 0.0
        total_emis = 0.0
        is_feasible = True
        
        for i in range(len(path) - 1):
            u, v = str(path[i]), str(path[i+1])
            if not self.graph.has_edge(u, v):
                return {
                    "distance_km": 0.0,
                    "travel_time_min": float('inf'),
                    "cost": float('inf'),
                    "emissions_g": float('inf'),
                    "is_feasible": False
                }
            metrics = self.get_edge_metrics(u, v, weights)
            if metrics["is_closed"] or metrics["cost"] == float('inf'):
                is_feasible = False
                total_cost = float('inf')
                total_time = float('inf')
                break
            total_dist += metrics["distance_km"]
            total_time += metrics["travel_time_min"]
            total_cost += metrics["cost"]
            total_emis += metrics["emissions_g"]
            
        return {
            "distance_km": round(total_dist, 3),
            "travel_time_min": round(total_time, 2) if is_feasible else float('inf'),
            "cost": round(total_cost, 3) if is_feasible else float('inf'),
            "emissions_g": round(total_emis, 1) if is_feasible else float('inf'),
            "is_feasible": is_feasible
        }

    def get_haversine_distance(self, node1: str, node2: str) -> float:
        """Great circle distance in kilometers."""
        lat1, lon1 = self.get_node_coords(node1)
        lat2, lon2 = self.get_node_coords(node2)
        
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        radius_earth_km = 6371.0
        return radius_earth_km * c

    def to_geojson(self) -> Dict[str, Any]:
        features = []
        # Nodes
        for node_id, data in self.graph.nodes(data=True):
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [data["lon"], data["lat"]]
                },
                "properties": {
                    "id": node_id,
                    "name": data.get("name", node_id),
                    "type": "node"
                }
            })
            
        # Edges
        for u, v, data in self.graph.edges(data=True):
            u_node = self.graph.nodes[u]
            v_node = self.graph.nodes[v]
            coords = data.get("geometry") or [
                [u_node["lon"], u_node["lat"]],
                [v_node["lon"], v_node["lat"]]
            ]
            
            metrics = self.get_edge_metrics(u, v)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "u": u,
                    "v": v,
                    "name": data.get("name", f"{u}->{v}"),
                    "length_km": data.get("length_km", 1.0),
                    "free_flow_speed_kmh": data.get("free_flow_speed_kmh", 50.0),
                    "capacity_vph": data.get("capacity_vph", 1500.0),
                    "current_flow_vph": data.get("current_flow_vph", 500.0),
                    "road_type": data.get("road_type", "primary"),
                    "is_closed": data.get("is_closed", False),
                    "incident_multiplier": data.get("incident_multiplier", 1.0),
                    "travel_time_min": metrics["travel_time_min"],
                    "cost": metrics["cost"],
                    "type": "edge"
                }
            })
            
        return {
            "type": "FeatureCollection",
            "properties": {
                "graph_id": self.graph_id,
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges()
            },
            "features": features
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoadGraph":
        rg = cls(graph_id=data.get("graph_id", "imported_network"))
        for node in data.get("nodes", []):
            rg.add_node(
                node_id=str(node["id"]),
                lat=node["lat"],
                lon=node["lon"],
                name=node.get("name", ""),
                metadata=node.get("metadata", {})
            )
        for edge in data.get("edges", []):
            rg.add_edge(
                u=str(edge["u"]),
                v=str(edge["v"]),
                length_km=edge["length_km"],
                free_flow_speed_kmh=edge.get("free_flow_speed_kmh", 50.0),
                capacity_vph=edge.get("capacity_vph", 1500.0),
                current_flow_vph=edge.get("current_flow_vph", 500.0),
                road_type=edge.get("road_type", "primary"),
                is_closed=edge.get("is_closed", False),
                incident_multiplier=edge.get("incident_multiplier", 1.0),
                geometry=edge.get("geometry", []),
                name=edge.get("name", "")
            )
        return rg
