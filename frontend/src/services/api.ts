import type {
  NetworkGeoJSON,
  OptimizeRouteResponse,
  ScenarioPreset,
  QAOAExecutionResponse,
  VRPResponse,
  Landmark,
  SystemStatus,
  RealWorldRouteResponse,
  TravelTimeMatrixResponse,
  RealWorldVRPRequest,
  RealWorldVRPResponse,
  PlaceSearchResult,
  PlaceResolution
} from '../types';

const API_BASE = '/api/v1';

export async function fetchNetwork(graphId: string = 'visakhapatnam_network'): Promise<NetworkGeoJSON> {
  const res = await fetch(`${API_BASE}/network?graph_id=${encodeURIComponent(graphId)}`);
  if (!res.ok) throw new Error(`Failed to fetch network: ${res.statusText}`);
  return res.json();
}

export async function optimizeRoute(params: {
  graph_id?: string;
  origin_node: string;
  destination_node: string;
  algorithms?: string[];
  weights?: Record<string, number>;
  max_iterations?: number;
  population_size?: number;
}): Promise<OptimizeRouteResponse> {
  const res = await fetch(`${API_BASE}/route/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      graph_id: params.graph_id || 'visakhapatnam_network',
      origin_node: params.origin_node,
      destination_node: params.destination_node,
      algorithms: params.algorithms || ['dijkstra', 'astar', 'aco', 'qpso'],
      weights: params.weights || { time: 0.5, distance: 0.2, congestion: 0.2, emissions: 0.1 },
      max_iterations: params.max_iterations || 35,
      population_size: params.population_size || 20,
      seed: 42
    })
  });
  if (!res.ok) throw new Error(`Optimization failed: ${res.statusText}`);
  return res.json();
}

export async function optimizeVRP(params: {
  graph_id?: string;
  depot_node?: string;
  customers?: {
    node_id: string;
    name: string;
    demand_kg: number;
    time_window_start_min: number;
    time_window_end_min: number;
    service_duration_min: number;
  }[];
  num_vehicles?: number;
  vehicle_capacity_kg?: number;
}): Promise<VRPResponse> {
  const defaultCustomers = [
    { node_id: '1', name: 'RK Beach Hub', demand_kg: 100.0, time_window_start_min: 0.0, time_window_end_min: 120.0, service_duration_min: 10.0 },
    { node_id: '2', name: 'Siripuram Store', demand_kg: 80.0, time_window_start_min: 0.0, time_window_end_min: 90.0, service_duration_min: 10.0 },
    { node_id: '3', name: 'Jagadamba Commercial', demand_kg: 120.0, time_window_start_min: 15.0, time_window_end_min: 150.0, service_duration_min: 10.0 },
    { node_id: '5', name: 'MVP Colony Retail', demand_kg: 90.0, time_window_start_min: 0.0, time_window_end_min: 100.0, service_duration_min: 10.0 },
    { node_id: '6', name: 'Rushikonda Tech Park', demand_kg: 110.0, time_window_start_min: 30.0, time_window_end_min: 180.0, service_duration_min: 10.0 }
  ];

  const res = await fetch(`${API_BASE}/vrp/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      problem_id: 'vizag_fleet_cvrp_dispatch',
      graph_id: params.graph_id || 'visakhapatnam_network',
      depot_node: params.depot_node || '4', // Maddilapalem
      customers: params.customers || defaultCustomers,
      num_vehicles: params.num_vehicles || 2,
      vehicle_capacity_kg: params.vehicle_capacity_kg || 300.0,
      max_iterations: 30,
      population_size: 20,
      seed: 42
    })
  });
  if (!res.ok) throw new Error(`VRP Optimization failed: ${res.statusText}`);
  return res.json();
}

export async function injectIncident(params: {
  graph_id?: string;
  u: string;
  v: string;
  incident_type?: string;
  multiplier?: number;
  is_closed?: boolean;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/traffic/incident`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      graph_id: params.graph_id || 'visakhapatnam_network',
      u: params.u,
      v: params.v,
      incident_type: params.incident_type || 'ROAD_BLOCK',
      multiplier: params.multiplier ?? 2.5,
      is_closed: params.is_closed ?? true
    })
  });
  if (!res.ok) throw new Error(`Failed to inject incident: ${res.statusText}`);
  return res.json();
}

export async function resetTraffic(graph_id: string = 'visakhapatnam_network'): Promise<any> {
  const res = await fetch(`${API_BASE}/traffic/reset?graph_id=${encodeURIComponent(graph_id)}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`Failed to reset traffic: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarios(): Promise<ScenarioPreset[]> {
  const res = await fetch(`${API_BASE}/simulation/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch scenarios: ${res.statusText}`);
  return res.json();
}

export async function runQAOA(payload?: any): Promise<QAOAExecutionResponse> {
  const defaultPayload = {
    problem_name: 'vizag_emergency_corridor_dispatch',
    num_variables: 4,
    variable_labels: ['Ambulance_BeachRoad', 'Ambulance_BRTS', 'FireTruck_BeachRoad', 'FireTruck_BRTS'],
    q_matrix: [
      [-5.0, 20.0, 15.0,  0.0],
      [ 0.0, -2.0,  0.0,  0.0],
      [ 0.0,  0.0, -4.0, 20.0],
      [ 0.0,  0.0,  0.0, -1.0]
    ],
    p_layers: 2
  };
  const res = await fetch(`${API_BASE}/quantum/qaoa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || defaultPayload)
  });
  if (!res.ok) throw new Error(`QAOA Execution failed: ${res.statusText}`);
  return res.json();
}

// =====================================================================
// REAL-WORLD SEARCH, GEOCODING & ROUTING APIS
// =====================================================================

export async function searchPlaces(query: string, limit: number = 10): Promise<PlaceSearchResult[]> {
  const clean = query.trim();
  if (!clean || clean.length < 2) return [];
  const res = await fetch(`${API_BASE}/search/places?query=${encodeURIComponent(clean)}&limit=${limit}`);
  if (!res.ok) throw new Error(`Place search failed: ${res.statusText}`);
  return res.json();
}

export async function geocodeForward(query: string): Promise<PlaceSearchResult> {
  const res = await fetch(`${API_BASE}/geocoding/forward?query=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(`Geocoding failed: ${res.statusText}`);
  return res.json();
}

export async function fetchLandmarks(query?: string): Promise<{ landmarks: Landmark[] }> {
  const url = query ? `${API_BASE}/landmarks?query=${encodeURIComponent(query)}` : `${API_BASE}/landmarks`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch landmarks: ${res.statusText}`);
  return res.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error(`Failed to fetch system status: ${res.statusText}`);
  return res.json();
}

export async function routeRealWorld(params: {
  origin_id?: string;
  destination_id?: string;
  origin_lat?: number;
  origin_lon?: number;
  dest_lat?: number;
  dest_lon?: number;
  origin_name?: string;
  dest_name?: string;
  origin_place?: PlaceSearchResult;
  dest_place?: PlaceSearchResult;
  alternatives?: boolean;
}): Promise<RealWorldRouteResponse> {
  const res = await fetch(`${API_BASE}/route/realworld`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Real-world routing failed: ${res.statusText}`);
  }
  return res.json();
}

export async function resolvePlace(place: {
  name: string;
  latitude: number;
  longitude: number;
  address?: string;
  category?: string;
  provider_place_id?: string;
  entry_points?: Array<{ type: string; position: { lat: number; lon: number } }>;
}): Promise<PlaceResolution> {
  const res = await fetch(`${API_BASE}/place/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: place.name,
      lat: place.latitude,
      lon: place.longitude,
      address: place.address || '',
      category: place.category || 'place',
      provider_place_id: place.provider_place_id || '',
      entry_points: place.entry_points
    })
  });
  if (!res.ok) throw new Error(`Place resolution failed: ${res.statusText}`);
  return res.json();
}

export async function debugRoute(origin: string, destination: string): Promise<any> {
  const res = await fetch(`${API_BASE}/route/debug`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ origin, destination })
  });
  if (!res.ok) throw new Error(`Route debug failed: ${res.statusText}`);
  return res.json();
}

export async function fetchTravelTimeMatrix(landmark_ids: string[]): Promise<TravelTimeMatrixResponse> {
  const res = await fetch(`${API_BASE}/route/matrix`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ landmark_ids })
  });
  if (!res.ok) throw new Error(`Failed to compute travel-time matrix: ${res.statusText}`);
  return res.json();
}

export async function optimizeRealWorldVRP(params: RealWorldVRPRequest): Promise<RealWorldVRPResponse> {
  const res = await fetch(`${API_BASE}/vrp/realworld`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `VRP optimization failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchLiveTraffic(): Promise<any> {
  const res = await fetch(`${API_BASE}/traffic/live`);
  if (!res.ok) throw new Error(`Failed to fetch live traffic: ${res.statusText}`);
  return res.json();
}

export async function trafficReoptimizeFleet(params: any): Promise<any> {
  const res = await fetch(`${API_BASE}/vrp/traffic_reoptimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Fleet traffic reoptimization failed: ${res.statusText}`);
  }
  return res.json();
}

