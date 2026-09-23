from typing import Dict, List, Any, Optional
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem
from optimization.vrp.vrp_baselines import GreedyVRP
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP

class VRPService:
    def __init__(self, graphs: Dict[str, RoadGraph]):
        self.graphs = graphs
        self.greedy = GreedyVRP()
        self.qpso_vrp = RandomKeyQPSOVRP()

    def _route_to_geojson(self, graph: RoadGraph, path: List[str], vehicle_id: int) -> Optional[Dict[str, Any]]:
        if not path or len(path) < 2:
            return None
            
        coordinates = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            if graph.graph.has_edge(u, v):
                edge_data = graph.graph[u][v]
                geom = edge_data.get("geometry")
                if geom and len(geom) >= 2:
                    coordinates.extend(geom)
                else:
                    u_node = graph.graph.nodes[u]
                    v_node = graph.graph.nodes[v]
                    coordinates.append([u_node["lon"], u_node["lat"]])
                    coordinates.append([v_node["lon"], v_node["lat"]])
                    
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {
                "vehicle_id": vehicle_id,
                "path_nodes": path
            }
        }

    def optimize_vrp(self, problem: VRPProblem) -> Dict[str, Any]:
        graph = self.graphs.get(problem.graph_id) or self.graphs.get("visakhapatnam_network")
        if not graph:
            raise ValueError(f"Graph '{problem.graph_id}' not found")
            
        greedy_res = self.greedy.solve(graph, problem)
        qpso_res = self.qpso_vrp.solve(graph, problem)
        
        # Attach GeoJSON to vehicle routes
        for r in greedy_res.routes:
            # We can compute path coordinates
            pass
            
        routes_geojson = []
        colors = ["#10b981", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6"]
        
        for idx, r in enumerate(qpso_res.routes):
            gj = self._route_to_geojson(graph, r.full_path_nodes, r.vehicle_id)
            if gj:
                gj["properties"]["color"] = colors[idx % len(colors)]
                gj["properties"]["total_load_kg"] = r.total_load_kg
                gj["properties"]["total_time_min"] = r.total_travel_time_min
                routes_geojson.append(gj)
                
        # Calculate improvement vs Greedy baseline
        base_time = greedy_res.total_fleet_time_min
        base_cost = greedy_res.total_fleet_cost
        qpso_time = qpso_res.total_fleet_time_min
        qpso_cost = qpso_res.total_fleet_cost
        
        time_imp = ((base_time - qpso_time) / base_time) * 100.0 if base_time > 0 else 0.0
        cost_imp = ((base_cost - qpso_cost) / base_cost) * 100.0 if base_cost > 0 else 0.0
        
        return {
            "status": "SUCCESS",
            "problem_id": problem.problem_id,
            "graph_id": problem.graph_id,
            "depot_node": problem.depot_node,
            "num_vehicles": problem.num_vehicles,
            "vehicle_capacity_kg": problem.vehicle_capacity_kg,
            "baseline": greedy_res.model_dump(),
            "qpso": qpso_res.model_dump(),
            "qpso_routes_geojson": {
                "type": "FeatureCollection",
                "features": routes_geojson
            },
            "improvements": {
                "travel_time_improvement_pct": round(time_imp, 2),
                "cost_improvement_pct": round(cost_imp, 2)
            },
            "provenance": {
                "road_network": "REAL DATA (OSM Visakhapatnam)",
                "traffic": "SIMULATED (BPR Engine)",
                "cost": "DERIVED",
                "optimization": "OPTIMIZATION RESULT (Random-Key QPSO)"
            }
        }
