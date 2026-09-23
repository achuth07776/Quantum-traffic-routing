export interface PlaceSearchResult {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  category?: string;
  provider: string;
  provider_place_id: string;
  entry_points?: Array<{
    type: string;
    position: { lat: number; lon: number };
  }>;
}

export interface PlaceResolution {
  provider: string;
  provider_place_id: string;
  name: string;
  address: string;
  category: string;
  latitude: number;
  longitude: number;
  access_latitude: number;
  access_longitude: number;
  access_road_name: string;
  snap_distance_m: number;
  resolution_method: string;
  confidence: 'HIGH' | 'MEDIUM' | 'REVIEW' | 'INVALID';
  entry_points_available: number;
}

export interface GeoJSONFeature {
  type: string;
  geometry: {
    type: string;
    coordinates: any;
  };
  properties: {
    id?: string;
    name?: string;
    u?: string;
    v?: string;
    length_km?: number;
    free_flow_speed_kmh?: number;
    capacity_vph?: number;
    current_flow_vph?: number;
    road_type?: string;
    is_closed?: boolean;
    incident_multiplier?: number;
    travel_time_min?: number;
    cost?: number;
    type?: string;
    color?: string;
    vehicle_id?: number;
    total_load_kg?: number;
    total_time_min?: number;
  };
}

export interface NetworkGeoJSON {
  type: string;
  properties: {
    graph_id: string;
    node_count: number;
    edge_count: number;
  };
  features: GeoJSONFeature[];
}

export interface SingleAlgorithmResult {
  algorithm_name: string;
  path: string[];
  distance_km: number;
  travel_time_min: number;
  cost: number;
  emissions_g: number;
  runtime_ms: number;
  iterations: number;
  convergence_curve: number[];
  is_feasible: boolean;
  path_geojson?: any;
  metadata?: Record<string, any>;
}

export interface OptimizeRouteResponse {
  status: string;
  graph_id: string;
  origin_node: string;
  destination_node: string;
  baseline_algorithm: string;
  results: Record<string, SingleAlgorithmResult>;
  improvements: Record<string, {
    travel_time_improvement_pct: number;
    composite_cost_improvement_pct: number;
    emissions_reduction_pct: number;
  }>;
  provenance?: Record<string, string>;
  timestamp: string;
}

export interface VehicleRouteData {
  vehicle_id: number;
  customer_nodes: string[];
  full_path_nodes: string[];
  total_load_kg: number;
  total_travel_time_min: number;
  total_distance_km: number;
  total_cost: number;
  time_window_penalties: number;
  is_feasible: boolean;
}

export interface VRPResponse {
  status: string;
  problem_id: string;
  graph_id: string;
  depot_node: string;
  num_vehicles: number;
  vehicle_capacity_kg: number;
  baseline: {
    algorithm_name: string;
    routes: VehicleRouteData[];
    total_fleet_time_min: number;
    total_fleet_distance_km: number;
    total_fleet_cost: number;
    unserved_customers: string[];
    runtime_ms: number;
    is_feasible: boolean;
  };
  qpso: {
    algorithm_name: string;
    routes: VehicleRouteData[];
    total_fleet_time_min: number;
    total_fleet_distance_km: number;
    total_fleet_cost: number;
    unserved_customers: string[];
    runtime_ms: number;
    iterations: number;
    convergence_curve: number[];
    is_feasible: boolean;
  };
  qpso_routes_geojson: {
    type: string;
    features: GeoJSONFeature[];
  };
  improvements: {
    travel_time_improvement_pct: number;
    cost_improvement_pct: number;
  };
  provenance: Record<string, string>;
}

export interface ScenarioPreset {
  scenario_id: string;
  title: string;
  description: string;
  city: string;
  origin_node: string;
  destination_node: string;
  incidents: {
    graph_id: string;
    u: string;
    v: string;
    incident_type: string;
    multiplier: number;
    is_closed: boolean;
  }[];
}

export interface QAOAExecutionResponse {
  status: string;
  optimal_bitstring: string;
  optimal_state_label: string;
  optimal_cost: number;
  ground_state_energy: number;
  qaoa_layers: number;
  optimal_gamma: number[];
  optimal_beta: number[];
  state_probabilities: Record<string, number>;
  quantum_circuit_qasm: string;
  circuit_depth: number;
  qubit_count: number;
  runtime_ms: number;
  is_converged: boolean;
}

export interface Landmark {
  id: string;
  name: string;
  lat: number;
  lon: number;
  category: string;
}

export interface RouteStep {
  instruction: string;
  road_name: string;
  distance_m: number;
  duration_s: number;
}

export interface RealWorldRouteResponse {
  status: string;
  provider: string;
  origin: { lat: number; lon: number; name: string };
  destination: { lat: number; lon: number; name: string };
  why_this_route?: string;
  traffic?: {
    provider: string;
    state: string;
    observations_used: number;
    coverage_pct: number;
    matched_length_m: number;
    total_length_m: number;
    free_flow_duration_s?: number;
    traffic_duration_s?: number;
    traffic_delay_s?: number;
  };
  speed_sanity?: {
    status: 'VALID' | 'SUSPICIOUS' | string;
    avg_speed_kmh: number;
    reason: string;
  };
  step_conservation?: {
    status: 'PASSED' | 'VIOLATED' | string;
    dist_diff_m: number;
    dur_diff_s: number;
  };
  traffic_rerouting?: {
    is_rerouted: boolean;
    reroute_reason?: string | null;
    old_duration_min?: number | null;
    new_duration_min?: number | null;
    time_saved_min?: number | null;
    recommended_route_index: number;
  };
  primary_route: {
    distance_m: number;
    distance_km: number;
    duration_s: number;
    duration_min: number;
    free_flow_duration_s?: number;
    free_flow_duration_min?: number;
    traffic_duration_s?: number;
    traffic_duration_min?: number;
    traffic_delay_s?: number;
    traffic_delay_min?: number;
    traffic_source?: string;
    traffic_freshness?: string;
    jam_factor_avg?: number;
    traversed_corridors?: string[];
    geometry_geojson: {
      type: string;
      coordinates: [number, number][];
    };
    steps: RouteStep[];
    provider: string;
    speed_sanity?: {
      status: 'VALID' | 'SUSPICIOUS' | string;
      avg_speed_kmh: number;
      reason: string;
    };
  };
  alternative_routes: Array<{
    index: number;
    distance_m: number;
    distance_km: number;
    duration_s: number;
    duration_min: number;
    free_flow_duration_min?: number;
    traffic_duration_min?: number;
    traffic_delay_min?: number;
    is_blocked?: boolean;
    geometry_geojson: {
      type: string;
      coordinates: [number, number][];
    };
    provider: string;
    why_this_route?: string;
    traffic?: any;
    speed_sanity?: {
      status: 'VALID' | 'SUSPICIOUS' | string;
      avg_speed_kmh: number;
      reason: string;
    };
  }>;
  origin_resolution?: PlaceResolution;
  destination_resolution?: PlaceResolution;
  location_advisory?: string;
  computation_ms: number;
  provenance: Record<string, any>;
  timestamp: string;
}

export interface SystemStatus {
  routing_engine: {
    provider: string;
    status: string;
    type: string;
  };
  traffic_source: {
    provider: string;
    status: string;
  };
  network_source: {
    provider: string;
    status: string;
  };
  provenance?: Record<string, any>;
}

export interface TravelTimeMatrixResponse {
  status: string;
  provider: string;
  landmark_ids: string[];
  landmark_names: string[];
  durations_s: number[][];
  distances_m: number[][];
  computation_ms: number;
  provenance?: Record<string, any>;
}

export interface FleetStop {
  id?: string;
  name: string;
  lat: number;
  lon: number;
  demand_kg: number;
}

export interface FleetDepot {
  id?: string;
  name: string;
  lat: number;
  lon: number;
}

export interface RealWorldVRPRequest {
  depot_id?: string;
  customer_ids?: string[];
  depot?: FleetDepot;
  customers?: FleetStop[];
  num_vehicles?: number;
  vehicle_capacity_kg?: number;
  customer_demands?: number[];
  max_route_time_min?: number;
  time_limit_seconds?: number;
  weights?: Record<string, number>;
}

export interface RealWorldVRPResponse {
  status: string;
  benchmark_comparison: {
    reference_solver: string;
    quantum_inspired_solver: string;
    baseline_solver: string;
    objective_function: {
      name: string;
      formula: string;
      weights: { time: number; distance: number };
      reference_scales?: {
        t_ref_min: number;
        d_ref_km: number;
        scale_interpretation?: string;
      };
    };
    qpso_cost_gap_vs_reference_pct?: number | null;
    qpso_gap_vs_reference_pct: number | null;
    qpso_time_gap_pct?: number | null;
    qpso_dist_gap_pct?: number | null;
    greedy_cost_gap_vs_reference_pct?: number | null;
    greedy_gap_vs_reference_pct: number | null;
    // Backward compatibility aliases
    gold_standard?: string;
    quantum_inspired?: string;
    baseline?: string;
    qpso_gap_vs_ortools_pct?: number | null;
    greedy_gap_vs_ortools_pct?: number | null;
    raw_savings_vs_greedy?: {
      time_saved_min: number;
      distance_saved_km: number;
      cost_saved: number;
    };
  };
  results: {
    ortools: {
      algorithm_name: string;
      routes: Array<{
        vehicle_id: number;
        customer_nodes: string[];
        full_path_nodes: string[];
        total_load_kg: number;
        total_travel_time_min: number;
        total_distance_km: number;
        total_cost: number;
      }>;
      total_fleet_time_min: number;
      total_fleet_distance_km: number;
      total_fleet_cost: number;
      runtime_ms: number;
      is_feasible: boolean;
      status?: string;
      objective?: {
        name: string;
        formula: string;
        weights: { time: number; distance: number };
        objective_value: number;
        components: { travel_time_min: number; distance_km: number };
      };
    };
    qpso: {
      algorithm_name: string;
      routes: Array<{
        vehicle_id: number;
        customer_nodes: string[];
        full_path_nodes: string[];
        total_load_kg: number;
        total_travel_time_min: number;
        total_distance_km: number;
        total_cost: number;
      }>;
      total_fleet_time_min: number;
      total_fleet_distance_km: number;
      total_fleet_cost: number;
      runtime_ms: number;
      is_feasible: boolean;
      objective?: {
        name: string;
        formula: string;
        weights: { time: number; distance: number };
        objective_value: number;
        components: { travel_time_min: number; distance_km: number };
      };
    };
    greedy: {
      algorithm_name: string;
      routes: Array<{
        vehicle_id: number;
        customer_nodes: string[];
        full_path_nodes: string[];
        total_load_kg: number;
        total_travel_time_min: number;
        total_distance_km: number;
        total_cost: number;
      }>;
      total_fleet_time_min: number;
      total_fleet_distance_km: number;
      total_fleet_cost: number;
      runtime_ms: number;
      is_feasible: boolean;
      objective?: {
        name: string;
        formula: string;
        weights: { time: number; distance: number };
        objective_value: number;
        components: { travel_time_min: number; distance_km: number };
      };
    };
  };
  matrix_metadata: {
    num_stops: number;
    num_vehicles: number;
    depot: string;
    matrix_engine: string;
    routing_profile?: string;
    matrix_status?: string;
    matrix_timestamp?: string;
  };
  stops_metadata?: Landmark[];
  matrix?: {
    durations_min: number[][];
    distances_km: number[][];
  };
  matrix_provenance?: {
    matrix_generated_at?: string;
    traffic_snapshot_id?: string;
    routing_provider?: string;
    routing_profile?: string;
    network_source?: string;
    customer_stops_source?: string;
    vehicle_capacity_source?: string;
    reference_solver?: string;
    summary_statement?: string;
    matrix_id?: string;
    traffic_state?: string;
    demand_provenance?: string;
    telemetry?: Record<string, any>;
  };
}

export interface FleetReoptimizationRequest {
  depot_id: string;
  customer_ids: string[];
  num_vehicles?: number;
  vehicle_capacity_kg?: number;
  customer_demands?: number[];
  max_route_time_min?: number;
  target_corridor_id?: string;
  simulated_incident_multiplier?: number;
  simulated_closed?: boolean;
}

export interface FleetReoptimizationResponse {
  status: string;
  experiment_title: string;
  provenance_statement?: string;
  optimization_run_id?: string;
  corridor_targeted: string;
  traffic_condition: string;
  stops_metadata: Landmark[];
  fixed_reference_scales?: {
    t_ref_min: number;
    d_ref_km: number;
    provenance: string;
  };
  value_of_reoptimization: {
    ortools: {
      t0_baseline_time_min: number;
      shocked_old_plan_time_min: number;
      reoptimized_time_min: number;
      time_saved_by_reoptimization_min: number;
      pct_delay_reduction?: number;
      shocked_old_plan_distance_km?: number;
      reoptimized_distance_km?: number;
      distance_added_km?: number;
      j_cost_saved_by_reoptimization: number;
      j_t0: number;
      j_shocked_old_plan: number;
      j_reoptimized: number;
      tours_diverged: boolean;
      baseline_routes: string[][];
      reoptimized_routes: string[][];
    };
    qpso: {
      t0_baseline_time_min: number;
      shocked_old_plan_time_min: number;
      reoptimized_time_min: number;
      time_saved_by_reoptimization_min: number;
      pct_delay_reduction?: number;
      shocked_old_plan_distance_km?: number;
      reoptimized_distance_km?: number;
      distance_added_km?: number;
      j_cost_saved_by_reoptimization: number;
      j_t0: number;
      j_shocked_old_plan: number;
      j_reoptimized: number;
      tours_diverged: boolean;
      baseline_routes: string[][];
      reoptimized_routes: string[][];
    };
    hero_summary: string;
  };
  four_quadrant_experiment_table: Array<{
    condition: string;
    solver: string;
    routes: string[][];
    fleet_time_min: number;
    fleet_dist_km: number;
    composite_j: number;
    is_feasible: boolean;
  }>;
  telemetry_latency_breakdown: {
    matrix_t0_generation_ms: number;
    solve_t0_ms: number;
    matrix_t1_generation_ms: number;
    traffic_fusion_ms: number;
    evaluation_old_plan_ms: number;
    solve_t1_ms: number;
    total_measured_stages_ms: number;
    total_request_ms: number;
    latency_explanation: string;
  };
  data_lineage?: Record<string, any>;
  fleet_divergence?: {
    tours_diverged: boolean;
    baseline_routes: string[][];
    reoptimized_routes: string[][];
    time_delta_min: number;
    cost_delta: number;
    summary: string;
  };
}
