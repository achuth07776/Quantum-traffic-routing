import os
import csv
import json
import time
import numpy as np
from typing import List, Dict, Any, Tuple
from app.domain.graph import RoadGraph
from optimization.vrp.vrp_models import VRPProblem, CustomerStop
from optimization.vrp.exact_vrp import ExactExhaustiveVRP
from optimization.vrp.vrp_baselines import GreedyVRP
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP
from optimization.baselines.dijkstra import DijkstraOptimizer
from optimization.baselines.astar import AStarOptimizer
from optimization.quantum_inspired.qpso import QPSOOptimizer
from optimization.interfaces.optimizer import RoutingProblem
from experiments.synthetic_generator import generate_synthetic_road_network, generate_synthetic_vrp_problem
from experiments.statistics import compute_trial_statistics
from experiments.export_pack import export_final_research_pack
from experiments.generate_plots import generate_all_plots
from experiments.benchmark_memetic_vs_qpso import run_memetic_benchmark

def compute_route_edges(path: List[str]) -> set:
    if not path or len(path) < 2:
        return set()
    return {(path[i], path[i+1]) for i in range(len(path) - 1)}

def run_all_experiments():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "experiments")
    os.makedirs(output_dir, exist_ok=True)
    
    seeds = [42, 101, 7, 23, 88, 12, 99, 54, 31, 77]
    
    print("==========================================================")
    print("STARTING SIH SCIENTIFIC VALIDATION & BENCHMARK SUITE (v2.3)")
    print("==========================================================")
    
    # Load Visakhapatnam dual-corridor base graph
    vizag_path = os.path.join(os.path.dirname(__file__), "..", "data", "graphs", "visakhapatnam_network.json")
    with open(vizag_path, "r", encoding="utf-8") as f:
        vizag_data = json.load(f)
    vizag_graph = RoadGraph.from_dict(vizag_data)
    
    # ---------------------------------------------------------
    # Experiment 1: Exact VRP Validation (N=4, 5, 6)
    # ---------------------------------------------------------
    print("\n[EXPERIMENT 1] Evaluating Exact VRP vs Greedy Baseline vs Random-Key QPSO (10 Seeds)...")
    exact_solver = ExactExhaustiveVRP()
    greedy_solver = GreedyVRP()
    qpso_vrp = RandomKeyQPSOVRP(num_particles=25)
    
    vrp_exact_summary = []
    vrp_exact_raw_records = []
    
    for n_cust in [4, 5, 6]:
        all_candidate_nodes = ["1", "2", "3", "5", "6", "7", "8", "9", "10"]
        chosen_nodes = all_candidate_nodes[:n_cust]
        
        customers = [
            CustomerStop(
                node_id=nid,
                name=f"Stop_{nid}",
                demand_kg=80.0 + (int(nid) % 3) * 20.0,
                time_window_start_min=0.0,
                time_window_end_min=150.0,
                service_duration_min=10.0
            )
            for nid in chosen_nodes
        ]
        
        prob = VRPProblem(
            problem_id=f"vizag_cvrp_n{n_cust}",
            graph_id="visakhapatnam_network",
            depot_node="4",
            customers=customers,
            num_vehicles=2,
            vehicle_capacity_kg=300.0,
            max_route_time_min=180.0
        )
        
        # 1. Exact Global Optimum
        exact_res = exact_solver.solve(vizag_graph, prob)
        exact_cost = exact_res.total_fleet_cost
        
        trial_records = []
        for seed in seeds:
            prob.seed = seed
            g_res = greedy_solver.solve(vizag_graph, prob)
            g_gap = ((g_res.total_fleet_cost - exact_cost) / exact_cost * 100.0) if exact_cost > 0 else 0.0
            
            q_res = qpso_vrp.solve(vizag_graph, prob)
            q_gap = ((q_res.total_fleet_cost - exact_cost) / exact_cost * 100.0) if exact_cost > 0 else 0.0
            
            rec = {
                "problem_size": n_cust,
                "seed": seed,
                "exact_cost": exact_cost,
                "exact_time_min": exact_res.total_fleet_time_min,
                "greedy_cost": g_res.total_fleet_cost,
                "greedy_time_min": g_res.total_fleet_time_min,
                "greedy_gap_pct": round(g_gap, 2),
                "greedy_runtime_ms": g_res.runtime_ms,
                "qpso_cost": q_res.total_fleet_cost,
                "qpso_time_min": q_res.total_fleet_time_min,
                "qpso_gap_pct": round(q_gap, 2),
                "qpso_runtime_ms": q_res.runtime_ms,
                "qpso_feasible": q_res.is_feasible
            }
            vrp_exact_raw_records.append(rec)
            trial_records.append(rec)
            
        vrp_exact_summary.append({
            "problem_size": n_cust,
            "exact_optimal_cost": exact_cost,
            "exact_travel_time_min": exact_res.total_fleet_time_min,
            "greedy_mean_cost": round(float(np.mean([t["greedy_cost"] for t in trial_records])), 3),
            "greedy_mean_gap_pct": round(float(np.mean([t["greedy_gap_pct"] for t in trial_records])), 2),
            "greedy_mean_runtime_ms": round(float(np.mean([t["greedy_runtime_ms"] for t in trial_records])), 2),
            "qpso_mean_cost": round(float(np.mean([t["qpso_cost"] for t in trial_records])), 3),
            "qpso_mean_gap_pct": round(float(np.mean([t["qpso_gap_pct"] for t in trial_records])), 2),
            "qpso_mean_runtime_ms": round(float(np.mean([t["qpso_runtime_ms"] for t in trial_records])), 2),
            "qpso_feasibility_pct": round(sum(1 for t in trial_records if t["qpso_feasible"]) / len(trial_records) * 100.0, 1),
            "num_trials": len(seeds)
        })
        
    csv_exact_path = os.path.join(output_dir, "vrp_exact_benchmark_results.csv")
    with open(csv_exact_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=vrp_exact_raw_records[0].keys())
        writer.writeheader()
        writer.writerows(vrp_exact_raw_records)
    print(f"[OK] Saved Exact VRP Benchmark CSV to: {csv_exact_path}")
    
    # ---------------------------------------------------------
    # Experiment 2: Multi-Seed VRP Fleet Scalability (N=8, 12, 16) with PAIRED Statistics
    # ---------------------------------------------------------
    print("\n[EXPERIMENT 2] Evaluating Multi-Seed VRP Fleet Scalability with Paired Statistics across 10 Seeds...")
    synth_50 = generate_synthetic_road_network(num_nodes=50, seed=42)
    vrp_scale_summary = []
    vrp_scale_raw_records = []
    
    for n_stops in [8, 12, 16]:
        num_v = max(2, n_stops // 4)
        v_cap = 350.0
        
        g_costs, g_times, g_runtimes = [], [], []
        q_costs, q_times, q_runtimes, q_feasibles = [], [], [], []
        
        for seed in seeds:
            vrp_scale_prob = generate_synthetic_vrp_problem(
                graph=synth_50,
                num_customers=n_stops,
                num_vehicles=num_v,
                vehicle_capacity_kg=v_cap,
                seed=seed
            )
            
            g_res = greedy_solver.solve(synth_50, vrp_scale_prob)
            q_res = qpso_vrp.solve(synth_50, vrp_scale_prob)
            
            g_costs.append(g_res.total_fleet_cost)
            g_times.append(g_res.total_fleet_time_min)
            g_runtimes.append(g_res.runtime_ms)
            
            q_costs.append(q_res.total_fleet_cost)
            q_times.append(q_res.total_fleet_time_min)
            q_runtimes.append(q_res.runtime_ms)
            q_feasibles.append(q_res.is_feasible)
            
            vrp_scale_raw_records.append({
                "num_customers": n_stops,
                "seed": seed,
                "greedy_cost": g_res.total_fleet_cost,
                "greedy_time_min": g_res.total_fleet_time_min,
                "greedy_runtime_ms": g_res.runtime_ms,
                "qpso_cost": q_res.total_fleet_cost,
                "qpso_time_min": q_res.total_fleet_time_min,
                "qpso_runtime_ms": q_res.runtime_ms,
                "qpso_feasible": q_res.is_feasible
            })
            
        mean_g_cost_all = float(np.mean(g_costs))
        mean_g_time_all = float(np.mean(g_times))
        mean_g_runtime = float(np.mean(g_runtimes))
        mean_q_runtime = float(np.mean(q_runtimes))
        
        # Paired statistics on the feasible subset
        paired_g_costs = [g for g, f in zip(g_costs, q_feasibles) if f]
        paired_q_costs = [q for q, f in zip(q_costs, q_feasibles) if f]
        paired_g_times = [g for g, f in zip(g_times, q_feasibles) if f]
        paired_q_times = [q for q, f in zip(q_times, q_feasibles) if f]
        
        mean_q_cost_feasible = float(np.mean(paired_q_costs)) if paired_q_costs else float('nan')
        mean_g_cost_paired = float(np.mean(paired_g_costs)) if paired_g_costs else float('nan')
        mean_q_time_feasible = float(np.mean(paired_q_times)) if paired_q_times else float('nan')
        mean_g_time_paired = float(np.mean(paired_g_times)) if paired_g_times else float('nan')
        
        # Compute exact trial-by-trial paired deltas
        paired_cost_deltas = [((g - q) / g * 100.0) for g, q in zip(paired_g_costs, paired_q_costs)]
        paired_time_deltas = [((g - q) / g * 100.0) for g, q in zip(paired_g_times, paired_q_times)]
        
        mean_paired_cost_delta = round(float(np.mean(paired_cost_deltas)), 2) if paired_cost_deltas else 0.0
        mean_paired_time_delta = round(float(np.mean(paired_time_deltas)), 2) if paired_time_deltas else 0.0
        
        runtime_ratio = round(mean_q_runtime / mean_g_runtime, 1) if mean_g_runtime > 0 else 1.0
        feasibility_rate = round(sum(1 for f in q_feasibles if f) / len(q_feasibles) * 100.0, 1)
        
        vrp_scale_summary.append({
            "num_customers": n_stops,
            "num_vehicles": num_v,
            "greedy_mean_cost_all_trials": round(mean_g_cost_all, 3),
            "greedy_mean_cost_paired_subset": round(mean_g_cost_paired, 3) if not np.isnan(mean_g_cost_paired) else "N/A",
            "greedy_mean_time_all_trials": round(mean_g_time_all, 2),
            "greedy_mean_runtime_ms": round(mean_g_runtime, 2),
            "qpso_mean_cost_feasible_subset": round(mean_q_cost_feasible, 3) if not np.isnan(mean_q_cost_feasible) else "N/A",
            "qpso_std_cost_feasible_subset": round(float(np.std(paired_q_costs)), 3) if paired_q_costs else 0.0,
            "qpso_mean_time_feasible_subset": round(mean_q_time_feasible, 2) if not np.isnan(mean_q_time_feasible) else "N/A",
            "qpso_mean_runtime_ms": round(mean_q_runtime, 2),
            "mean_paired_cost_delta_pct": mean_paired_cost_delta,
            "mean_paired_time_delta_pct": mean_paired_time_delta,
            "runtime_ratio": runtime_ratio,
            "feasibility_rate_pct": feasibility_rate,
            "num_trials": len(seeds),
            "status_note": "FEASIBLE" if feasibility_rate == 100.0 else f"BUDGET LIMITED ({feasibility_rate}% feasible)"
        })
        
    csv_vrp_scale_path = os.path.join(output_dir, "vrp_scalability_multi_seed.csv")
    with open(csv_vrp_scale_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=vrp_scale_raw_records[0].keys())
        writer.writeheader()
        writer.writerows(vrp_scale_raw_records)
    print(f"[OK] Saved VRP Scalability CSV to: {csv_vrp_scale_path}")
    
    # ---------------------------------------------------------
    # Experiment 3: Dynamic Traffic Reoptimization Benchmark (Dual Corridor) with Overlap Metrics
    # ---------------------------------------------------------
    print("\n[EXPERIMENT 3] Evaluating Dynamic Traffic Reoptimization, Route Diversion & Edge Overlap...")
    scenarios_to_test = [
        {
            "id": "NORMAL_FLOW",
            "name": "1. Free Flow Baseline (Coastal Corridor Dominant)",
            "origin": "1", "dest": "6",
            "mutations": [],
            "expected_alternative_exists": True
        },
        {
            "id": "RUSHIKONDA_LANDSLIDE",
            "name": "2. Coastal Expressway Landslide (5->6 Closed -> Divert to Simhachalam Bypass)",
            "origin": "1", "dest": "6",
            "mutations": [{"u": "5", "v": "6", "multiplier": 1.0, "closed": True}],
            "expected_alternative_exists": True
        },
        {
            "id": "MADDILAPALEM_FLOOD_AND_CLOSURE",
            "name": "3. Maddilapalem Waterlogging (Moderate 3.5x Delay)",
            "origin": "1", "dest": "6",
            "mutations": [{"u": "4", "v": "5", "multiplier": 3.5, "closed": False}, {"u": "2", "v": "4", "multiplier": 3.0, "closed": False}],
            "expected_alternative_exists": True
        },
        {
            "id": "PORT_CONTAINER_FREIGHT_SPIKE",
            "name": "4. Port Corridor Freight Spike (9->3 3.5x Delay -> Alternative Port Route)",
            "origin": "9", "dest": "7",
            "mutations": [{"u": "9", "v": "3", "multiplier": 3.5, "closed": False}],
            "expected_alternative_exists": True
        },
        {
            "id": "TOTAL_RUSHIKONDA_ISOLATION",
            "name": "5. Total Destination Isolation (All Inbound Links Closed -> True Failure Test)",
            "origin": "1", "dest": "6",
            "mutations": [
                {"u": "5", "v": "6", "multiplier": 1.0, "closed": True},
                {"u": "11", "v": "6", "multiplier": 1.0, "closed": True},
                {"u": "12", "v": "6", "multiplier": 1.0, "closed": True}
            ],
            "expected_alternative_exists": False
        }
    ]
    
    dynamic_traffic_summary = []
    astar_solver = AStarOptimizer()
    qpso_route_solver = QPSOOptimizer(num_particles=25)
    
    for sc in scenarios_to_test:
        sc_graph = RoadGraph.from_dict(vizag_data)
        
        for m in sc["mutations"]:
            sc_graph.update_incident(m["u"], m["v"], m["multiplier"], m["closed"])
            
        prob_sc = RoutingProblem(
            graph_id="visakhapatnam_network",
            origin=sc["origin"],
            destination=sc["dest"],
            weights={"time": 0.5, "distance": 0.2, "congestion": 0.2, "emissions": 0.1},
            max_iterations=40,
            population_size=25,
            seed=42
        )
        
        # 1. Normal pre-shock reference route
        pre_shock_res = astar_solver.solve(vizag_graph, prob_sc)
        
        # 2. Post-shock solutions on mutated graph
        shock_astar = astar_solver.solve(sc_graph, prob_sc)
        shock_qpso = qpso_route_solver.solve(sc_graph, prob_sc)
        
        # Compute Edge Overlap & Route Change
        pre_edges = compute_route_edges(pre_shock_res.path) if pre_shock_res.is_feasible else set()
        shock_edges = compute_route_edges(shock_qpso.path) if shock_qpso.is_feasible else set()
        
        if pre_edges and shock_edges:
            intersection = pre_edges.intersection(shock_edges)
            union = pre_edges.union(shock_edges)
            overlap_pct = round(len(intersection) / len(union) * 100.0, 1) if union else 0.0
            route_change_pct = round(100.0 - overlap_pct, 1)
        else:
            overlap_pct = 0.0
            route_change_pct = 100.0 if shock_qpso.is_feasible else 0.0
            
        route_diverted = (
            shock_qpso.is_feasible and 
            shock_qpso.path != pre_shock_res.path and 
            len(shock_qpso.path) > 0
        )
        
        alternative_available = shock_astar.is_feasible or shock_qpso.is_feasible
        
        dynamic_traffic_summary.append({
            "scenario_id": sc["id"],
            "scenario_name": sc["name"],
            "origin": sc["origin"],
            "destination": sc["dest"],
            "pre_shock_route": " -> ".join(pre_shock_res.path) if pre_shock_res.is_feasible else "None",
            "pre_shock_time_min": pre_shock_res.travel_time_min if pre_shock_res.is_feasible else "N/A",
            "pre_shock_cost": pre_shock_res.cost if pre_shock_res.is_feasible else "N/A",
            "shock_astar_route": " -> ".join(shock_astar.path) if shock_astar.is_feasible else "NO FEASIBLE ROUTE",
            "shock_astar_time_min": shock_astar.travel_time_min if shock_astar.is_feasible else "Infinity",
            "shock_astar_cost": shock_astar.cost if shock_astar.is_feasible else "Infinity",
            "shock_qpso_route": " -> ".join(shock_qpso.path) if shock_qpso.is_feasible else "NO FEASIBLE ROUTE",
            "shock_qpso_time_min": shock_qpso.travel_time_min if shock_qpso.is_feasible else "Infinity",
            "shock_qpso_cost": shock_qpso.cost if shock_qpso.is_feasible else "Infinity",
            "route_diverted_around_shock": route_diverted,
            "route_overlap_pct": overlap_pct,
            "route_change_pct": route_change_pct,
            "alternative_feasible_route_available": alternative_available,
            "qpso_feasible": shock_qpso.is_feasible,
            "qpso_runtime_ms": shock_qpso.runtime_ms
        })
        
    csv_dynamic_path = os.path.join(output_dir, "dynamic_traffic_benchmark.csv")
    with open(csv_dynamic_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dynamic_traffic_summary[0].keys())
        writer.writeheader()
        writer.writerows(dynamic_traffic_summary)
    print(f"[OK] Saved Dynamic Traffic Benchmark CSV to: {csv_dynamic_path}")
    
    # ---------------------------------------------------------
    # Experiment 4: QPSO Parameter Sensitivity Study (500-Node Graph)
    # ---------------------------------------------------------
    print("\n[EXPERIMENT 4] Evaluating QPSO Parameter Sensitivity on 500-Node Network...")
    synth_500 = generate_synthetic_road_network(num_nodes=500, seed=42)
    prob_500 = RoutingProblem(
        graph_id=synth_500.graph_id,
        origin="1",
        destination="500",
        seed=42
    )
    
    sensitivity_records = []
    for pop in [10, 20, 30, 50]:
        for iters in [15, 30, 50, 100]:
            sens_qpso = QPSOOptimizer(num_particles=pop)
            prob_500.population_size = pop
            prob_500.max_iterations = iters
            
            res_sens = sens_qpso.solve(synth_500, prob_500)
            sensitivity_records.append({
                "population_particles": pop,
                "iteration_budget": iters,
                "is_feasible": res_sens.is_feasible,
                "cost": res_sens.cost if res_sens.is_feasible else "Infinity",
                "travel_time_min": res_sens.travel_time_min if res_sens.is_feasible else "Infinity",
                "runtime_ms": res_sens.runtime_ms
            })
            
    csv_sens_path = os.path.join(output_dir, "qpso_parameter_sensitivity.csv")
    with open(csv_sens_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sensitivity_records[0].keys())
        writer.writeheader()
        writer.writerows(sensitivity_records)
    print(f"[OK] Saved Parameter Sensitivity CSV to: {csv_sens_path}")
    
    # ---------------------------------------------------------
    # Experiment 5: Point-to-Point Scalability (N=15 to N=500)
    # ---------------------------------------------------------
    print("\n[EXPERIMENT 5] Evaluating Point-to-Point Routing Scalability (N=15 to N=500)...")
    scalability_records = []
    dijkstra = DijkstraOptimizer()
    
    for num_nodes in [15, 50, 100, 250, 500]:
        if num_nodes == 15:
            test_graph = vizag_graph
            origin, dest = "1", "6"
        else:
            test_graph = generate_synthetic_road_network(num_nodes=num_nodes, seed=42)
            origin, dest = "1", str(num_nodes)
            
        prob_route = RoutingProblem(
            graph_id=test_graph.graph_id,
            origin=origin,
            destination=dest,
            max_iterations=30,
            population_size=20,
            seed=42
        )
        
        res_d = dijkstra.solve(test_graph, prob_route)
        res_a = astar_solver.solve(test_graph, prob_route)
        res_q = qpso_route_solver.solve(test_graph, prob_route)
        
        scalability_records.append({
            "graph_nodes": num_nodes,
            "graph_edges": test_graph.graph.number_of_edges(),
            "dijkstra_runtime_ms": res_d.runtime_ms,
            "dijkstra_cost": res_d.cost if res_d.is_feasible else "Infinity",
            "astar_runtime_ms": res_a.runtime_ms,
            "astar_time_min": res_a.travel_time_min if res_a.is_feasible else "Infinity",
            "qpso_runtime_ms": res_q.runtime_ms,
            "qpso_cost": res_q.cost if res_q.is_feasible else "Infinity",
            "qpso_feasible": res_q.is_feasible,
            "status_note": "FEASIBLE" if res_q.is_feasible else "INFEASIBLE (20p x 30i Limit)"
        })
        
    csv_scale_path = os.path.join(output_dir, "scalability_benchmark_results.csv")
    with open(csv_scale_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=scalability_records[0].keys())
        writer.writeheader()
        writer.writerows(scalability_records)
    print(f"[OK] Saved Point-to-Point Scalability CSV to: {csv_scale_path}")
    
    # ---------------------------------------------------------
    # Experiment 6: Memetic Hybrid Benchmark (Vanilla QPSO vs Memetic QPSO)
    # ---------------------------------------------------------
    print("\n[EXPERIMENT 6] Evaluating Memetic Hybrid QPSO (QPSO + 2-Opt/Relocate Local Search) vs Vanilla QPSO...")
    memetic_raw_records, memetic_summary, memetic_aggregate = run_memetic_benchmark(
        output_dir=output_dir,
        scales=[8, 12, 16],
        seeds=seeds,
        particles=20,
        iterations=30,
        ls_rounds=2,
        improvement_mode="best"
    )
    print(f"[OK] Saved Memetic vs Vanilla QPSO benchmark to: {output_dir}/memetic_vs_qpso_benchmark.csv")
    
    # ---------------------------------------------------------
    # Generate Consolidated Statistical Summary JSON
    # ---------------------------------------------------------
    summary_data = {
        "vrp_exact_summary": vrp_exact_summary,
        "vrp_scalability_summary": vrp_scale_summary,
        "dynamic_traffic_summary": dynamic_traffic_summary,
        "scalability_summary": scalability_records,
        "parameter_sensitivity_summary": sensitivity_records,
        "memetic_vs_qpso_summary": memetic_summary,
        "memetic_hybrid_aggregate": memetic_aggregate,
        "search_configuration": {
            "point_to_point_qpso": {"particles": 20, "max_iterations": 30, "beta": "1.0 -> 0.5"},
            "vrp_qpso": {"particles": 25, "max_iterations": 50, "beta": "1.0 -> 0.5"},
            "memetic_qpso": {"particles": 20, "max_iterations": 30, "beta": "1.0 -> 0.5", "local_search": "2-opt + relocate, best-improvement"},
            "evaluated_seeds": seeds
        },
        "provenance_statement": "Comprehensive empirical scientific validation framework evaluated across 10 deterministic random seeds with exact exhaustive references, paired VRP statistical analysis, dual-corridor dynamic traffic reoptimization, single-seed parameter sensitivity analysis, and paired vanilla-vs-memetic hybrid QPSO benchmarking."
    }
    
    json_summary_path = os.path.join(output_dir, "statistical_summary.json")
    with open(json_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"[OK] Saved Consolidated Statistical Summary JSON to: {json_summary_path}")
    
    # Automatically export final results pack & research plots
    print("\n----------------------------------------------------------")
    print("EXPORTING STANDARDIZED RESEARCH PACK & GENERATING PLOTS")
    print("----------------------------------------------------------")
    export_final_research_pack()
    generate_all_plots()
    
    print("\nALL 6 SCIENTIFIC EXPERIMENTS & PLOTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_experiments()
