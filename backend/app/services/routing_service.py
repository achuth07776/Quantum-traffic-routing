import datetime
from typing import Dict, List, Any, Optional
from app.domain.graph import RoadGraph
from app.schemas.routing import OptimizeRouteRequest, OptimizeRouteResponse, SingleAlgorithmResultSchema
from optimization.interfaces.optimizer import RoutingProblem, BaseOptimizer
from optimization.baselines.dijkstra import DijkstraOptimizer
from optimization.baselines.astar import AStarOptimizer
from optimization.metaheuristics.aco import ACOOptimizer
from optimization.quantum_inspired.qpso import QPSOOptimizer

class RoutingService:
    def __init__(self, graphs: Dict[str, RoadGraph]):
        self.graphs = graphs
        self.optimizers: Dict[str, BaseOptimizer] = {
            "dijkstra": DijkstraOptimizer(),
            "astar": AStarOptimizer(),
            "aco": ACOOptimizer(num_ants=20),
            "qpso": QPSOOptimizer(num_particles=25)
        }

    def _path_to_geojson(self, graph: RoadGraph, path: List[str]) -> Optional[Dict[str, Any]]:
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
                "path_nodes": path
            }
        }

    def optimize(self, req: OptimizeRouteRequest) -> OptimizeRouteResponse:
        graph = self.graphs.get(req.graph_id)
        if not graph:
            raise ValueError(f"Graph '{req.graph_id}' not found")
            
        problem = RoutingProblem(
            graph_id=req.graph_id,
            origin=req.origin_node,
            destination=req.destination_node,
            weights=req.weights,
            max_iterations=req.max_iterations,
            population_size=req.population_size,
            seed=req.seed
        )
        
        results_map: Dict[str, SingleAlgorithmResultSchema] = {}
        
        # 1. Run requested algorithms
        algo_keys = req.algorithms if req.algorithms else ["dijkstra", "astar", "aco", "qpso"]
        
        for algo_key in algo_keys:
            opt = self.optimizers.get(algo_key.lower())
            if not opt:
                continue
            
            res = opt.solve(graph, problem)
            path_geojson = self._path_to_geojson(graph, res.path) if res.is_feasible else None
            
            results_map[algo_key.lower()] = SingleAlgorithmResultSchema(
                algorithm_name=res.algorithm_name,
                path=res.path,
                distance_km=res.distance_km,
                travel_time_min=res.travel_time_min,
                cost=res.cost,
                emissions_g=res.emissions_g,
                runtime_ms=res.runtime_ms,
                iterations=res.iterations,
                convergence_curve=res.convergence_curve,
                is_feasible=res.is_feasible,
                path_geojson=path_geojson,
                metadata=res.metadata
            )
            
        # 2. Compute improvements relative to Dijkstra baseline
        baseline_key = "dijkstra" if "dijkstra" in results_map else (list(results_map.keys())[0] if results_map else "none")
        improvements: Dict[str, Dict[str, float]] = {}
        
        if baseline_key in results_map and results_map[baseline_key].is_feasible:
            base_time = results_map[baseline_key].travel_time_min
            base_cost = results_map[baseline_key].cost
            base_emis = results_map[baseline_key].emissions_g
            
            for k, v in results_map.items():
                if k == baseline_key or not v.is_feasible:
                    continue
                time_imp = ((base_time - v.travel_time_min) / base_time) * 100.0 if base_time > 0 else 0.0
                cost_imp = ((base_cost - v.cost) / base_cost) * 100.0 if base_cost > 0 else 0.0
                emis_imp = ((base_emis - v.emissions_g) / base_emis) * 100.0 if base_emis > 0 else 0.0
                
                improvements[k] = {
                    "travel_time_improvement_pct": round(time_imp, 2),
                    "composite_cost_improvement_pct": round(cost_imp, 2),
                    "emissions_reduction_pct": round(emis_imp, 2)
                }
                
        return OptimizeRouteResponse(
            status="SUCCESS",
            graph_id=req.graph_id,
            origin_node=req.origin_node,
            destination_node=req.destination_node,
            baseline_algorithm=baseline_key,
            results=results_map,
            improvements=improvements,
            provenance={
                "road_network": "REAL DATA (OSM Visakhapatnam)",
                "traffic": "SIMULATED (BPR Non-Linear Engine)",
                "cost": "DERIVED",
                "optimization": "OPTIMIZATION RESULT",
                "emissions": "ESTIMATED"
            },
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
