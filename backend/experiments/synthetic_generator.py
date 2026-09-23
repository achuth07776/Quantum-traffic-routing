import math
import random
import numpy as np
from typing import Dict, List, Tuple
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem, CustomerStop

def generate_synthetic_road_network(num_nodes: int = 50, grid_size: int = 10, seed: int = 42) -> RoadGraph:
    """
    Generates a realistic connected synthetic urban road network with 2D coordinates,
    arterial and secondary road classifications, capacities, and base flows.
    """
    random.seed(seed)
    np.random.seed(seed)
    
    rg = RoadGraph(f"synthetic_network_{num_nodes}")
    
    # Base center at Visakhapatnam coordinates
    base_lat, base_lon = 17.725, 83.315
    
    # Generate nodes on perturbed spatial grid
    nodes = []
    side = int(math.ceil(math.sqrt(num_nodes)))
    spacing_km = 1.5
    
    for i in range(num_nodes):
        r = i // side
        c = i % side
        # Perturb slightly
        lat_offset = (r * spacing_km + random.uniform(-0.3, 0.3)) / 111.0
        lon_offset = (c * spacing_km + random.uniform(-0.3, 0.3)) / (111.0 * math.cos(math.radians(base_lat)))
        
        node_id = str(i + 1)
        node_lat = base_lat + lat_offset
        node_lon = base_lon + lon_offset
        
        rg.add_node(node_id, node_lat, node_lon, f"Junction_{node_id}")
        nodes.append(node_id)
        
    # Connect nearest neighbors (k-NN) to ensure strong connectivity
    for i, u in enumerate(nodes):
        # Find distances to other nodes
        dists = []
        for j, v in enumerate(nodes):
            if i != j:
                d = rg.get_haversine_distance(u, v)
                dists.append((d, v))
                
        dists.sort(key=lambda x: x[0])
        # Connect to 3-4 nearest neighbors bidirectionally
        num_neighbors = min(len(dists), random.randint(2, 4))
        for d, v in dists[:num_neighbors]:
            if not rg.graph.has_edge(u, v):
                is_trunk = d > 2.0
                speed = 60.0 if is_trunk else 40.0
                cap = 3000.0 if is_trunk else 1800.0
                flow = cap * random.uniform(0.3, 0.7)
                rg.add_edge(
                    u=u, v=v,
                    length_km=round(d, 2),
                    free_flow_speed_kmh=speed,
                    capacity_vph=cap,
                    current_flow_vph=round(flow, 1),
                    road_type="trunk" if is_trunk else "primary"
                )
            if not rg.graph.has_edge(v, u):
                d_rev = rg.get_haversine_distance(v, u)
                rg.add_edge(
                    u=v, v=u,
                    length_km=round(d_rev, 2),
                    free_flow_speed_kmh=50.0,
                    capacity_vph=2000.0,
                    current_flow_vph=round(2000.0 * 0.4, 1),
                    road_type="primary"
                )
                
    return rg

def generate_synthetic_vrp_problem(
    graph: RoadGraph,
    num_customers: int = 6,
    num_vehicles: int = 2,
    vehicle_capacity_kg: float = 300.0,
    seed: int = 42
) -> VRPProblem:
    """
    Generates a deterministic synthetic VRP instance on the provided graph.
    """
    random.seed(seed)
    node_ids = list(graph.nodes)
    
    depot = node_ids[0]
    candidate_stops = node_ids[1 : min(len(node_ids), num_customers + 1)]
    
    customers = []
    for idx, c_node in enumerate(candidate_stops):
        demand = random.choice([60.0, 80.0, 100.0, 120.0])
        tw_start = random.choice([0.0, 15.0, 30.0])
        tw_end = tw_start + random.choice([90.0, 120.0, 180.0])
        customers.append(CustomerStop(
            node_id=c_node,
            name=f"Customer_{c_node}",
            demand_kg=demand,
            time_window_start_min=tw_start,
            time_window_end_min=tw_end,
            service_duration_min=10.0
        ))
        
    return VRPProblem(
        problem_id=f"synthetic_vrp_N{num_customers}_V{num_vehicles}",
        graph_id=graph.graph_id,
        depot_node=depot,
        customers=customers,
        num_vehicles=num_vehicles,
        vehicle_capacity_kg=vehicle_capacity_kg,
        max_route_time_min=180.0,
        seed=seed
    )
