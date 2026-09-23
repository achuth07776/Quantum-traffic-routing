from typing import Dict, List, Any, Optional
from app.domain.graph import RoadGraph
from app.schemas.simulation import IncidentInjectionRequest, ScenarioPreset

class TrafficService:
    def __init__(self, graphs: Dict[str, RoadGraph]):
        self.graphs = graphs
        self.active_incidents: Dict[str, List[Dict[str, Any]]] = {}

    def get_graph(self, graph_id: str) -> Optional[RoadGraph]:
        return self.graphs.get(graph_id) or self.graphs.get("visakhapatnam_network")

    def inject_incident(self, req: IncidentInjectionRequest) -> Dict[str, Any]:
        graph = self.get_graph(req.graph_id)
        if not graph:
            raise ValueError(f"Graph '{req.graph_id}' not found")
            
        success = graph.update_incident(
            u=req.u,
            v=req.v,
            incident_multiplier=req.multiplier,
            is_closed=req.is_closed
        )
        if not success:
            raise ValueError(f"Edge ({req.u} -> {req.v}) not found in graph '{req.graph_id}'")
            
        if req.graph_id not in self.active_incidents:
            self.active_incidents[req.graph_id] = []
            
        self.active_incidents[req.graph_id].append({
            "u": req.u,
            "v": req.v,
            "incident_type": req.incident_type,
            "multiplier": req.multiplier,
            "is_closed": req.is_closed
        })
        
        updated_metrics = graph.get_edge_metrics(req.u, req.v)
        return {
            "status": "SUCCESS",
            "u": req.u,
            "v": req.v,
            "is_closed": req.is_closed,
            "incident_multiplier": req.multiplier,
            "updated_edge_metrics": updated_metrics
        }

    def reset_incidents(self, graph_id: str) -> Dict[str, Any]:
        graph = self.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph '{graph_id}' not found")
        graph.reset_incidents()
        self.active_incidents[graph_id] = []
        return {"status": "SUCCESS", "message": f"All incidents reset for graph '{graph_id}'"}

    def get_preset_scenarios(self) -> List[ScenarioPreset]:
        return [
            ScenarioPreset(
                scenario_id="scenario_vizag_maddilapalem_gridlock",
                title="Maddilapalem Flyover Monsoon Waterlogging",
                description="Heavy congestion and drainage overflow at Maddilapalem -> MVP Colony arterial with 3.5x delay multiplier",
                city="Visakhapatnam",
                origin_node="1", # RK Beach
                destination_node="6", # Rushikonda IT SEZ
                incidents=[
                    IncidentInjectionRequest(
                        graph_id="visakhapatnam_network",
                        u="4",
                        v="5",
                        incident_type="BOTTLENECK_SPIKE",
                        multiplier=3.5,
                        is_closed=False
                    )
                ]
            ),
            ScenarioPreset(
                scenario_id="scenario_vizag_rushikonda_coastal_erosion",
                title="Rushikonda Beach Road Coastal Landslide",
                description="Severe coastal erosion blocks MVP Colony -> Rushikonda IT Expressway directly",
                city="Visakhapatnam",
                origin_node="1", # RK Beach
                destination_node="6", # Rushikonda IT SEZ
                incidents=[
                    IncidentInjectionRequest(
                        graph_id="visakhapatnam_network",
                        u="5",
                        v="6",
                        incident_type="ROAD_BLOCK",
                        multiplier=1.0,
                        is_closed=True
                    )
                ]
            ),
            ScenarioPreset(
                scenario_id="scenario_vizag_port_container_shock",
                title="Port Freight Corridor Heavy Container Shock",
                description="Heavy freight bottleneck on Scindia -> Gajuwaka Industrial Highway",
                city="Visakhapatnam",
                origin_node="10", # Vizag Railway Station
                destination_node="15", # Steel Plant Main Gate
                incidents=[
                    IncidentInjectionRequest(
                        graph_id="visakhapatnam_network",
                        u="14",
                        v="8",
                        incident_type="BOTTLENECK_SPIKE",
                        multiplier=3.2,
                        is_closed=False
                    )
                ]
            ),
            ScenarioPreset(
                scenario_id="scenario_vizag_jagadamba_commercial",
                title="Jagadamba Cinema Road Festival Gridlock",
                description="Festive retail rush chokes Siripuram -> Jagadamba commercial junction",
                city="Visakhapatnam",
                origin_node="4", # Maddilapalem
                destination_node="10", # Railway Station
                incidents=[
                    IncidentInjectionRequest(
                        graph_id="visakhapatnam_network",
                        u="2",
                        v="3",
                        incident_type="BOTTLENECK_SPIKE",
                        multiplier=2.8,
                        is_closed=False
                    )
                ]
            )
        ]
