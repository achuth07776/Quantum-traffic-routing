import math
from typing import Dict, Optional

def calculate_bpr_travel_time(
    length_km: float,
    free_flow_speed_kmh: float,
    flow_vph: float,
    capacity_vph: float,
    incident_multiplier: float = 1.0,
    alpha: float = 0.15,
    beta: float = 4.0
) -> float:
    """
    Calculates dynamic travel time (in minutes) using the extended Bureau of Public Roads (BPR) function.
    
    Formula:
        t = (L / V_free) * 60 * [1 + alpha * (Flow / Capacity)^beta] * incident_multiplier
    """
    if free_flow_speed_kmh <= 0 or length_km <= 0:
        return 0.0
    
    free_flow_time_hours = length_km / free_flow_speed_kmh
    free_flow_time_minutes = free_flow_time_hours * 60.0
    
    vc_ratio = max(0.0, flow_vph / max(1.0, capacity_vph))
    congestion_factor = 1.0 + alpha * math.pow(vc_ratio, beta)
    
    return free_flow_time_minutes * congestion_factor * max(1.0, incident_multiplier)


def calculate_edge_emissions(
    length_km: float,
    travel_time_min: float,
    free_flow_speed_kmh: float
) -> float:
    """
    Estimates CO2 emissions (in grams) for a vehicle traversing the edge.
    Smooth cruising (~50 km/h) has baseline emission ~120 g CO2/km.
    Congested stop-and-go flow (actual speed < 20 km/h) scales emissions up to ~300 g/km.
    """
    if length_km <= 0 or travel_time_min <= 0:
        return 0.0
    
    effective_speed_kmh = (length_km / (travel_time_min / 60.0))
    speed_ratio = effective_speed_kmh / max(10.0, free_flow_speed_kmh)
    
    # Non-linear emission penalty when crawling in traffic
    if speed_ratio >= 0.8:
        emission_rate_g_per_km = 120.0
    elif speed_ratio >= 0.4:
        emission_rate_g_per_km = 120.0 + (0.8 - speed_ratio) * 200.0
    else:
        emission_rate_g_per_km = 200.0 + (0.4 - speed_ratio) * 300.0
        
    return length_km * emission_rate_g_per_km


def calculate_composite_cost(
    length_km: float,
    travel_time_min: float,
    flow_vph: float,
    capacity_vph: float,
    emissions_g: float,
    weights: Optional[Dict[str, float]] = None,
    is_closed: bool = False
) -> float:
    """
    Calculates normalized multi-objective scalar cost for routing optimization.
    Hard constraint: closed road returns infinity.
    """
    if is_closed:
        return float('inf')
        
    w = weights or {"time": 0.5, "distance": 0.2, "congestion": 0.2, "emissions": 0.1}
    
    vc_ratio = max(0.0, flow_vph / max(1.0, capacity_vph))
    
    # Normalized components:
    # 1 min time ≈ 1.0 unit
    # 1 km distance ≈ 0.8 unit
    # v/c ratio > 1.0 introduces steep congestion penalty
    # 100g CO2 ≈ 0.5 unit
    cost_time = travel_time_min
    cost_dist = length_km * 0.8
    cost_cong = math.pow(vc_ratio, 2) * 5.0
    cost_emis = (emissions_g / 100.0) * 0.5
    
    return (
        w.get("time", 0.5) * cost_time +
        w.get("distance", 0.2) * cost_dist +
        w.get("congestion", 0.2) * cost_cong +
        w.get("emissions", 0.1) * cost_emis
    )
