"""
Phase E5: Real-Network Fleet Optimization Benchmark under Fair Computational Budgets.

Conducts a Pareto-style algorithmic comparison between:
  1. Google OR-Tools Guided Local Search across time budgets (100ms, 250ms, 500ms, 1000ms, 2000ms reference)
  2. Random-Key QPSO across swarm configurations (P=10/I=15, P=20/I=30, P=30/I=50, P=50/I=100) and multiple seeds
  3. Greedy Nearest-Neighbor Baseline (single pass)

Evaluated across problem instance scales: 5, 10, 15, 20, 30, 40, 50 customers
using real OpenStreetMap road travel-time matrices from the OSRM Table API.
All algorithms evaluate the identical normalized dimensionless multi-objective:
  J = 0.7 * (T / T_ref) + 0.3 * (D / D_ref)
"""

import os
import csv
import json
import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import numpy as np

from transport.landmarks import LandmarkRegistry
from providers.routing.osrm import OSRMRoutingProvider
from providers.routing.base import Coords
from optimization.vrp.matrix_vrp import RealWorldVRPOptimizer


# Extended real Visakhapatnam delivery stops to support scales up to 50
EXTENDED_VIZAG_STOPS: List[Tuple[str, str, float, float]] = [
    # Curated landmark POIs (27 customers, excluding depot)
    ("rk_beach", "RK Beach", 17.7144, 83.3341),
    ("rushikonda_beach", "Rushikonda Beach / IT SEZ", 17.7818, 83.3854),
    ("nad_junction", "NAD Junction", 17.7482, 83.2189),
    ("kailasagiri_hill", "Kailasagiri Hill", 17.7540, 83.3724),
    ("visakhapatnam_port", "Visakhapatnam Port", 17.6975, 83.2842),
    ("gajuwaka_junction", "Gajuwaka Junction", 17.6896, 83.2128),
    ("simhachalam_temple", "Simhachalam Temple", 17.7685, 83.2421),
    ("visakhapatnam_railway_station", "Railway Station", 17.7214, 83.2981),
    ("siripuram_junction", "Siripuram Junction", 17.7226, 83.3156),
    ("mvp_colony", "MVP Colony", 17.7441, 83.3412),
    ("dwaraka_bus_station", "Dwaraka Bus Station", 17.7130, 83.2960),
    ("madhurawada", "Madhurawada", 17.7890, 83.3560),
    ("asilmetta_junction", "Asilmetta Junction", 17.7195, 83.3105),
    ("andhra_university", "Andhra University", 17.7300, 83.3190),
    ("gitam_university", "GITAM University", 17.7639, 83.3780),
    ("steel_plant_main_gate", "Steel Plant Main Gate", 17.6415, 83.1610),
    ("scindia_junction", "Scindia Junction", 17.6745, 83.2655),
    ("pendurthi", "Pendurthi", 17.8285, 83.1995),
    ("vims", "VIMS Hospital", 17.7520, 83.3130),
    ("king_george_hospital", "KGH Hospital", 17.7180, 83.3060),
    ("poorna_market", "Poorna Market", 17.7050, 83.2930),
    ("kancharapalem", "Kancharapalem", 17.7380, 83.2850),
    ("cmr_central_mall", "CMR Central", 17.7410, 83.2300),
    ("waltair_uplands", "Waltair Uplands", 17.7265, 83.3235),
    ("marripalem_vuda_park", "Marripalem VUDA Park", 17.7560, 83.3450),
    ("jagadamba_junction", "Jagadamba Junction", 17.7118, 83.3005),
    ("bheemili_beach", "Bheemili Beach", 17.8900, 83.4520),
    # Additional real Visakhapatnam delivery hubs for scales > 27
    ("mvp_sector_1", "MVP Sector 1", 17.7460, 83.3380),
    ("mvp_sector_6", "MVP Sector 6", 17.7420, 83.3450),
    ("madhurawada_it_hub", "Madhurawada IT Hub", 17.7950, 83.3610),
    ("madhurawada_stadium", "ACA-VDCA Cricket Stadium", 17.7980, 83.3540),
    ("rushikonda_tech_park", "Rushikonda Technology Park", 17.7850, 83.3810),
    ("gajuwaka_autonagar", "Autonagar Industrial Hub", 17.6950, 83.2050),
    ("gajuwaka_bhel", "BHEL Heavy Plates", 17.6820, 83.2180),
    ("kurmannapalem", "Kurmannapalem Junction", 17.6650, 83.1820),
    ("sheela_nagar", "Sheela Nagar", 17.7120, 83.2450),
    ("mindi_terminal", "HPCL Mindi Terminal", 17.6710, 83.2290),
    ("seethammadhara", "Seethammadhara NE", 17.7380, 83.3120),
    ("dwaraka_nagar_diamond_park", "Diamond Park", 17.7220, 83.3050),
    ("resapuvanipalem", "Resapuvanipalem", 17.7290, 83.3280),
    ("pedda_waltair", "Pedda Waltair", 17.7240, 83.3350),
    ("isukathota", "Isukathota Junction", 17.7470, 83.3290),
    ("venkojipalem", "Venkojipalem", 17.7550, 83.3370),
    ("hanumanthawaka", "Hanumanthawaka Junction", 17.7610, 83.3320),
    ("arilova_health_city", "Arilova Health City", 17.7720, 83.3280),
    ("pm_palem", "PM Palem", 17.8050, 83.3650),
    ("kommadhi", "Kommadhi Junction", 17.8180, 83.3690),
    ("gambheeram_sez", "Gambheeram SEZ", 17.8350, 83.3850),
    ("anandapuram", "Anandapuram Junction", 17.8650, 83.3810),
    ("sujatha_nagar", "Sujatha Nagar", 17.7780, 83.2210),
    ("chinamushidiwada", "Chinamushidiwada", 17.7890, 83.2120),
]

DEPOT: Tuple[str, str, float, float] = ("maddilapalem_junction", "Maddilapalem Depot", 17.7348, 83.3245)

SCALES = [5, 10, 15, 20, 30, 40, 50]
VEHICLES_PER_SCALE = {5: 2, 10: 3, 15: 4, 20: 5, 30: 7, 40: 9, 50: 10}

OR_TOOLS_BUDGETS_MS = [100, 250, 500, 1000, 2000]
QPSO_CONFIGS = [
    ("QPSO_P10_I15", 10, 15),
    ("QPSO_P20_I30", 20, 30),
    ("QPSO_P30_I50", 30, 50),
    ("QPSO_P50_I100", 50, 100),
]
SEEDS = [42, 101, 2024]


async def run_phase_e5_fair_benchmark():
    routing = OSRMRoutingProvider()
    optimizer = RealWorldVRPOptimizer()
    matrix_ts = datetime.now(timezone.utc).isoformat()

    all_records = []

    print("=" * 95)
    print("  PHASE E5: REAL-NETWORK VRP BENCHMARK WITH FAIR COMPUTATIONAL BUDGETS")
    print(f"  Matrix Engine: OSRM Table API | Timestamp: {matrix_ts}")
    print("=" * 95)

    for scale in SCALES:
        num_vehicles = VEHICLES_PER_SCALE[scale]
        stops = [DEPOT] + EXTENDED_VIZAG_STOPS[:scale]
        node_ids = [s[0] for s in stops]
        coords = [Coords(lat=s[2], lon=s[3]) for s in stops]

        print(f"\n[{scale} CUSTOMERS | {num_vehicles} VEHICLES | OSRM Matrix {scale+1}x{scale+1}]")

        try:
            matrix = await routing.table(coords)
        except Exception as e:
            print(f"  Error fetching matrix for {scale} customers: {e}")
            continue

        durations_min = [[round(s / 60.0, 2) for s in row] for row in matrix.durations_s]
        distances_km = [[round(m / 1000.0, 2) for m in row] for row in matrix.distances_m]
        demands = [0.0] + [50.0] * scale
        capacities = [300.0] * num_vehicles

        # Compute T_ref, D_ref
        valid_t = [durations_min[i][j] for i in range(len(stops)) for j in range(len(stops)) if i != j and durations_min[i][j]]
        valid_d = [distances_km[i][j] for i in range(len(stops)) for j in range(len(stops)) if i != j and distances_km[i][j]]
        t_ref = round(float(np.mean(valid_t)), 2) if valid_t else 1.0
        d_ref = round(float(np.mean(valid_d)), 2) if valid_d else 1.0

        # -------------------------------------------------------------
        # 1. Classical Heuristic: Greedy Nearest Neighbor (O(N^2))
        # -------------------------------------------------------------
        base_out = optimizer.solve_fleet_vrp(
            node_ids=node_ids,
            duration_matrix_min=durations_min,
            distance_matrix_km=distances_km,
            demands=demands,
            vehicle_capacities=capacities,
            depot_index=0,
            time_limit_seconds=2.0
        )
        greedy = base_out["results"]["greedy"]
        greedy_obj = greedy["total_fleet_cost"]
        greedy_time = greedy["total_fleet_time_min"]
        greedy_dist = greedy["total_fleet_distance_km"]
        greedy_runtime = greedy["runtime_ms"]

        all_records.append({
            "scale": scale,
            "num_vehicles": num_vehicles,
            "solver": "Greedy_NN",
            "mode": "Heuristic_Baseline",
            "budget_label": "Greedy_O(N^2)",
            "budget_ms": greedy_runtime,
            "seed": None,
            "is_feasible": greedy["is_feasible"],
            "raw_objective": greedy_obj,
            "raw_time_min": greedy_time,
            "raw_dist_km": greedy_dist,
            "runtime_ms": greedy_runtime,
            "gap_vs_ortools_2s_ref_pct": None,
            "gap_vs_greedy_pct": 0.0,
            "t_ref_min": t_ref,
            "d_ref_km": d_ref
        })

        # -------------------------------------------------------------
        # 2. Reference Solution: Google OR-Tools under 2-second budget
        # -------------------------------------------------------------
        ref_out = base_out["results"]["ortools"]
        ref_obj = ref_out["total_fleet_cost"]
        ref_time = ref_out["total_fleet_time_min"]
        ref_dist = ref_out["total_fleet_distance_km"]
        ref_runtime = ref_out["runtime_ms"]

        # Calculate greedy gap vs OR-Tools reference
        greedy_gap_vs_ref = round(((greedy_obj - ref_obj) / max(1e-6, ref_obj)) * 100.0, 2)
        all_records[-1]["gap_vs_ortools_2s_ref_pct"] = greedy_gap_vs_ref

        # -------------------------------------------------------------
        # 3. Mode A: OR-Tools Time Budget Sweeps (100ms - 2000ms)
        # -------------------------------------------------------------
        for b_ms in OR_TOOLS_BUDGETS_MS:
            ort_sweep = optimizer.solve_fleet_vrp(
                node_ids=node_ids,
                duration_matrix_min=durations_min,
                distance_matrix_km=distances_km,
                demands=demands,
                vehicle_capacities=capacities,
                depot_index=0,
                ortools_time_limit_ms=b_ms
            )
            ort_res = ort_sweep["results"]["ortools"]
            ort_cost = ort_res["total_fleet_cost"]
            ort_gap_vs_ref = round(((ort_cost - ref_obj) / max(1e-6, ref_obj)) * 100.0, 2)
            ort_gap_vs_greedy = round(((ort_cost - greedy_obj) / max(1e-6, greedy_obj)) * 100.0, 2)

            all_records.append({
                "scale": scale,
                "num_vehicles": num_vehicles,
                "solver": "Google_ORTools",
                "mode": "Equalized_Budget" if b_ms < 2000 else "Quality_Reference",
                "budget_label": f"ORT_{b_ms}ms",
                "budget_ms": b_ms,
                "seed": None,
                "is_feasible": ort_res["is_feasible"],
                "raw_objective": ort_cost,
                "raw_time_min": ort_res["total_fleet_time_min"],
                "raw_dist_km": ort_res["total_fleet_distance_km"],
                "runtime_ms": ort_res["runtime_ms"],
                "gap_vs_ortools_2s_ref_pct": ort_gap_vs_ref,
                "gap_vs_greedy_pct": ort_gap_vs_greedy,
                "t_ref_min": t_ref,
                "d_ref_km": d_ref
            })

        # -------------------------------------------------------------
        # 4. Mode A: QPSO Configuration & Repeated Seed Sweeps
        # -------------------------------------------------------------
        for cfg_name, particles, iters in QPSO_CONFIGS:
            for seed in SEEDS:
                qpso_sweep = optimizer.solve_fleet_vrp(
                    node_ids=node_ids,
                    duration_matrix_min=durations_min,
                    distance_matrix_km=distances_km,
                    demands=demands,
                    vehicle_capacities=capacities,
                    depot_index=0,
                    qpso_particles=particles,
                    qpso_iterations=iters,
                    qpso_seed=seed
                )
                qpso_res = qpso_sweep["results"]["qpso"]
                qpso_cost = qpso_res["total_fleet_cost"]
                qpso_gap_vs_ref = round(((qpso_cost - ref_obj) / max(1e-6, ref_obj)) * 100.0, 2)
                qpso_gap_vs_greedy = round(((qpso_cost - greedy_obj) / max(1e-6, greedy_obj)) * 100.0, 2)

                all_records.append({
                    "scale": scale,
                    "num_vehicles": num_vehicles,
                    "solver": "RandomKey_QPSO",
                    "mode": "Equalized_Budget",
                    "budget_label": cfg_name,
                    "budget_ms": qpso_res["runtime_ms"],
                    "seed": seed,
                    "is_feasible": qpso_res["is_feasible"],
                    "raw_objective": qpso_cost,
                    "raw_time_min": qpso_res["total_fleet_time_min"],
                    "raw_dist_km": qpso_res["total_fleet_distance_km"],
                    "runtime_ms": qpso_res["runtime_ms"],
                    "gap_vs_ortools_2s_ref_pct": qpso_gap_vs_ref,
                    "gap_vs_greedy_pct": qpso_gap_vs_greedy,
                    "t_ref_min": t_ref,
                    "d_ref_km": d_ref
                })

        # Progress log per scale
        ort_500 = next(r for r in all_records if r["scale"] == scale and r["budget_label"] == "ORT_500ms")
        qpso_std = next(r for r in all_records if r["scale"] == scale and r["budget_label"] == "QPSO_P20_I30" and r["seed"] == 42)
        print(f"  Greedy:   J = {greedy_obj:.4f} (Runtime: {greedy_runtime:.1f}ms)")
        print(f"  ORT 500m: J = {ort_500['raw_objective']:.4f} (Gap vs 2s Ref: {ort_500['gap_vs_ortools_2s_ref_pct']:+.2f}%)")
        print(f"  ORT 2000: J = {ref_obj:.4f} (Time: {ref_time:.1f}m, Dist: {ref_dist:.1f}km)")
        print(f"  QPSO P20: J = {qpso_std['raw_objective']:.4f} (Runtime: {qpso_std['runtime_ms']:.1f}ms, Gap vs Ref: {qpso_std['gap_vs_ortools_2s_ref_pct']:+.2f}%)")

    # Save complete dataset
    out_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "phase_e5_fair_budget_benchmark.csv")
    json_path = os.path.join(out_dir, "phase_e5_fair_budget_benchmark.json")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_records[0].keys())
        writer.writeheader()
        writer.writerows(all_records)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)

    print(f"\n[PHASE E5 BENCHMARK COMPLETE] Saved {len(all_records)} empirical records to:")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    asyncio.run(run_phase_e5_fair_benchmark())
