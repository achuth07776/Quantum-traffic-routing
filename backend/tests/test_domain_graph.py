import json
import pytest
from app.domain.bpr import calculate_bpr_travel_time, calculate_edge_emissions, calculate_composite_cost
from app.domain.graph import RoadGraph

def test_bpr_travel_time_monotonicity():
    # Free flow
    t_free = calculate_bpr_travel_time(length_km=10.0, free_flow_speed_kmh=60.0, flow_vph=0.0, capacity_vph=2000.0)
    assert round(t_free, 2) == 10.0  # 10 km at 60 km/h is exactly 10 min
    
    # Moderate traffic (flow = capacity)
    t_congested = calculate_bpr_travel_time(length_km=10.0, free_flow_speed_kmh=60.0, flow_vph=2000.0, capacity_vph=2000.0)
    assert t_congested > t_free
    assert round(t_congested, 2) == 11.5  # 10 * (1 + 0.15 * 1^4) = 11.5 min
    
    # Severe bottleneck (flow = 1.5 * capacity)
    t_severe = calculate_bpr_travel_time(length_km=10.0, free_flow_speed_kmh=60.0, flow_vph=3000.0, capacity_vph=2000.0)
    assert t_severe > t_congested
    
    # Incident multiplier
    t_incident = calculate_bpr_travel_time(length_km=10.0, free_flow_speed_kmh=60.0, flow_vph=2000.0, capacity_vph=2000.0, incident_multiplier=2.0)
    assert round(t_incident, 2) == round(t_congested * 2.0, 2)


def test_edge_emissions_crawling_penalty():
    # Free flow (60 km/h -> 10 min for 10 km)
    e_free = calculate_edge_emissions(length_km=10.0, travel_time_min=10.0, free_flow_speed_kmh=60.0)
    # Severe traffic (10 km taking 60 min -> 10 km/h)
    e_congested = calculate_edge_emissions(length_km=10.0, travel_time_min=60.0, free_flow_speed_kmh=60.0)
    assert e_congested > e_free


def test_road_graph_incident_update_and_geojson():
    rg = RoadGraph("test_network")
    rg.add_node("A", 12.91, 77.62, "Node A")
    rg.add_node("B", 12.93, 77.63, "Node B")
    rg.add_edge("A", "B", length_km=2.5, free_flow_speed_kmh=50.0, capacity_vph=1500.0, current_flow_vph=500.0)
    
    metrics = rg.get_edge_metrics("A", "B")
    assert metrics["is_closed"] is False
    assert metrics["cost"] > 0
    
    # Update incident to block road
    rg.update_incident("A", "B", is_closed=True)
    metrics_blocked = rg.get_edge_metrics("A", "B")
    assert metrics_blocked["is_closed"] is True
    assert metrics_blocked["cost"] == float('inf')
    
    # Reset
    rg.reset_incidents()
    metrics_reset = rg.get_edge_metrics("A", "B")
    assert metrics_reset["is_closed"] is False
    
    # GeoJSON
    geojson = rg.to_geojson()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 3  # 2 nodes + 1 edge
