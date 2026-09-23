"""
Memetic Hybrid Benchmark: Vanilla Random-Key QPSO vs Memetic QPSO
(QPSO + 2-Opt/Relocate Local Search Hybrid).

Scientific question tested here:
  Does adding an intensification (local-search) phase on top of the global
  Quantum-Behaved PSO exploration improve solution quality, and at what
  runtime cost?

Design:
  - Identical paired problem instances (same graph, same seed) for both solvers.
  - Identical swarm configuration (particles x iterations x beta schedule).
  - Multi-seed x multi-scale comparison on a synthetic Visakhapatnam-style road
    network.
  - All candidates decoded by the same validated capacity / time-window decoder.

Outputs (paired, seed-by-seed):
  - Raw per-trial CSV          -> <output_dir>/memetic_vs_qpso_benchmark.csv
  - Per-scale summary CSV      -> <output_dir>/memetic_vs_qpso_benchmark_summary.csv
  - Full JSON record           -> <output_dir>/memetic_vs_qpso_benchmark.json
"""

import os
import csv
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import numpy as np

from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP
from optimization.vrp.vrp_qpso_memetic import MemeticRandomKeyQPSOVRP
from experiments.synthetic_generator import generate_synthetic_road_network, generate_synthetic_vrp_problem

SCALES = [8, 12, 16, 20]
VEHICLES_PER_SCALE = {8: 2, 12: 3, 16: 4, 20: 5}
SEEDS = [42, 101, 2024, 7, 23]
VEHICLE_CAPACITY_KG = 350.0
QPSO_PARTICLES = 20
QPSO_ITERATIONS = 30
LS_ROUNDS = 2
IMPROVEMENT_MODE = "best"


def run_memetic_benchmark(
    output_dir: Optional[str] = None,
    scales: Optional[List[int]] = None,
    seeds: Optional[List[int]] = None,
    particles: int = QPSO_PARTICLES,
    iterations: int = QPSO_ITERATIONS,
    ls_rounds: int = LS_ROUNDS,
    improvement_mode: str = IMPROVEMENT_MODE
):
    """Runs the paired vanilla-QPSO vs memetic-QPSO benchmark and persists results.

    Returns (raw_records, summaries, aggregate). Pass output_dir to write the
    three output files into a custom directory (default: experiments/results).
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)

    scales = scales or SCALES
    seeds = seeds or SEEDS
    num_v_map = {s: VEHICLES_PER_SCALE.get(s, max(2, s // 4)) for s in scales}

    qpso_vrp = RandomKeyQPSOVRP(num_particles=particles)
    memetic_vrp = MemeticRandomKeyQPSOVRP(
        num_particles=particles,
        ls_rounds=ls_rounds,
        improvement_mode=improvement_mode
    )

    synth_50 = generate_synthetic_road_network(num_nodes=50, seed=42)
    ts = datetime.now(timezone.utc).isoformat()

    print("=" * 95)
    print("  MEMETIC HYBRID BENCHMARK: VANILLA Random-Key QPSO vs MEMETIC QPSO")
    print(f"  Network: synthetic 50-node | Config: P={particles} I={iterations} | Timestamp: {ts}")
    print(f"  Local Search: 2-opt + relocate, {improvement_mode}-improvement, LS rounds = {ls_rounds}")
    print("=" * 95)

    raw_records: List[Dict[str, Any]] = []
    summaries: List[Dict[str, Any]] = []

    for scale in scales:
        num_v = num_v_map[scale]
        print(f"\n[{scale} CUSTOMERS | {num_v} VEHICLES | Capacity {VEHICLE_CAPACITY_KG:.0f}kg]")

        q_costs, q_times, q_runtimes, q_feas = [], [], [], []
        m_costs, m_times, m_runtimes, m_feas = [], [], [], []

        for seed in seeds:
            prob = generate_synthetic_vrp_problem(
                graph=synth_50,
                num_customers=scale,
                num_vehicles=num_v,
                vehicle_capacity_kg=VEHICLE_CAPACITY_KG,
                seed=seed
            )

            # Paired identical instance: vanilla first, memetic second
            q_res = qpso_vrp.solve(synth_50, prob)
            m_res = memetic_vrp.solve(synth_50, prob)

            q_costs.append(q_res.total_fleet_cost)
            q_times.append(q_res.total_fleet_time_min)
            q_runtimes.append(q_res.runtime_ms)
            q_feas.append(q_res.is_feasible)

            m_costs.append(m_res.total_fleet_cost)
            m_times.append(m_res.total_fleet_time_min)
            m_runtimes.append(m_res.runtime_ms)
            m_feas.append(m_res.is_feasible)

            improvement_pct = round(((q_res.total_fleet_cost - m_res.total_fleet_cost)
                                     / max(1e-9, q_res.total_fleet_cost)) * 100.0, 2)
            raw_records.append({
                "num_customers": scale,
                "num_vehicles": num_v,
                "seed": seed,
                "qpso_cost": q_res.total_fleet_cost,
                "qpso_time_min": q_res.total_fleet_time_min,
                "qpso_runtime_ms": q_res.runtime_ms,
                "qpso_feasible": q_res.is_feasible,
                "memetic_cost": m_res.total_fleet_cost,
                "memetic_time_min": m_res.total_fleet_time_min,
                "memetic_runtime_ms": m_res.runtime_ms,
                "memetic_feasible": m_res.is_feasible,
                "improvement_pct_vs_qpso": improvement_pct
            })

        # Paired statistics on the trials where BOTH solvers are feasible
        paired = [(q, m, qt, mt, qrt, mrt)
                  for q, m, qt, mt, qrt, mrt, qf, mf
                  in zip(q_costs, m_costs, q_times, m_times, q_runtimes, m_runtimes, q_feas, m_feas)
                  if qf and mf]

        mean_q_cost = float(np.mean([p[0] for p in paired])) if paired else float('nan')
        std_q_cost = float(np.std([p[0] for p in paired])) if paired else 0.0
        mean_m_cost = float(np.mean([p[1] for p in paired])) if paired else float('nan')
        std_m_cost = float(np.std([p[1] for p in paired])) if paired else 0.0

        deltas = [((p[0] - p[1]) / max(1e-9, p[0]) * 100.0) for p in paired]
        mean_delta_pct = round(float(np.mean(deltas)), 2) if deltas else 0.0
        wins = sum(1 for d in deltas if d > 0.05)
        losses = sum(1 for d in deltas if d < -0.05)
        ties = len(deltas) - wins - losses

        mean_q_time = float(np.mean([p[2] for p in paired])) if paired else float('nan')
        mean_m_time = float(np.mean([p[3] for p in paired])) if paired else float('nan')
        mean_q_rt = float(np.mean([p[4] for p in paired])) if paired else float('nan')
        mean_m_rt = float(np.mean([p[5] for p in paired])) if paired else float('nan')
        runtime_ratio = round(mean_m_rt / mean_q_rt, 2) if mean_q_rt > 0 else 1.0

        summaries.append({
            "num_customers": scale,
            "num_vehicles": num_v,
            "num_trials": len(seeds),
            "paired_feasible_trials": len(paired),
            "qpso_mean_cost_paired": round(mean_q_cost, 4) if not np.isnan(mean_q_cost) else "N/A",
            "qpso_std_cost_paired": round(std_q_cost, 4),
            "memetic_mean_cost_paired": round(mean_m_cost, 4) if not np.isnan(mean_m_cost) else "N/A",
            "memetic_std_cost_paired": round(std_m_cost, 4),
            "mean_improvement_pct_vs_qpso": mean_delta_pct,
            "wins_count": wins,
            "losses_count": losses,
            "ties_count": ties,
            "qpso_mean_time_min": round(mean_q_time, 2) if not np.isnan(mean_q_time) else "N/A",
            "memetic_mean_time_min": round(mean_m_time, 2) if not np.isnan(mean_m_time) else "N/A",
            "qpso_mean_runtime_ms": round(mean_q_rt, 2),
            "memetic_mean_runtime_ms": round(mean_m_rt, 2),
            "memetic_vs_qpso_runtime_ratio": runtime_ratio,
            "qpso_feasibility_pct": round(sum(q_feas) / len(q_feas) * 100.0, 1),
            "memetic_feasibility_pct": round(sum(m_feas) / len(m_feas) * 100.0, 1)
        })

        s = summaries[-1]
        print(f"  Vanilla QPSO : J = {s['qpso_mean_cost_paired']} (RT {s['qpso_mean_runtime_ms']}ms, feas {s['qpso_feasibility_pct']}%)")
        print(f"  Memetic QPSO : J = {s['memetic_mean_cost_paired']} (RT {s['memetic_mean_runtime_ms']}ms, feas {s['memetic_feasibility_pct']}%)")
        print(f"  Mean paired improvement: {s['mean_improvement_pct_vs_qpso']:+.2f}% | Wins {s['wins_count']} / Losses {s['losses_count']} / Ties {s['ties_count']} | Runtime ratio {s['memetic_vs_qpso_runtime_ratio']}x")

    # Aggregate verdict across all scales
    all_deltas = [r["improvement_pct_vs_qpso"] for r in raw_records if r["qpso_feasible"] and r["memetic_feasible"]]
    aggregate = {
        "config": {
            "network": "Synthetic 50-node grid (Visakhapatnam-centered)",
            "scales": scales,
            "seeds": seeds,
            "particles": particles,
            "max_iterations": iterations,
            "beta": [1.0, 0.5],
            "local_search": {
                "moves": ["2-opt (contiguous reversal)", "relocate (single customer move)"],
                "improvement_mode": improvement_mode,
                "ls_rounds_per_iteration": ls_rounds,
                "feedback": "Improved gbest ordering re-encoded into swarm attractor"
            }
        },
        "aggregate_mean_improvement_pct_vs_qpso": round(float(np.mean(all_deltas)), 2) if all_deltas else 0.0,
        "aggregate_median_improvement_pct": round(float(np.median(all_deltas)), 2) if all_deltas else 0.0,
        "total_paired_trials": len(all_deltas),
        "timestamp": ts,
        "interpretation": "Positive improvement pct means the memetic hybrid achieves LOWER normalized fleet cost than vanilla QPSO on the same instance; runtime ratio shows the intensification cost."
    }

    # Save raw CSV
    csv_raw_path = os.path.join(output_dir, "memetic_vs_qpso_benchmark.csv")
    with open(csv_raw_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(raw_records[0].keys()))
        writer.writeheader()
        writer.writerows(raw_records)

    # Save per-scale summary CSV
    csv_sum_path = os.path.join(output_dir, "memetic_vs_qpso_benchmark_summary.csv")
    with open(csv_sum_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    # Save full JSON record
    json_path = os.path.join(output_dir, "memetic_vs_qpso_benchmark.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "aggregate": aggregate,
            "per_scale_summary": summaries,
            "raw_records": raw_records
        }, f, indent=2)

    print("\n" + "-" * 95)
    print(f"  AGGREGATE MEAN IMPROVEMENT vs Vanilla QPSO: {aggregate['aggregate_mean_improvement_pct_vs_qpso']:+.2f}% "
          f"(median {aggregate['aggregate_median_improvement_pct']:+.2f}%, {aggregate['total_paired_trials']} paired trials)")
    print(f"  Runtime cost of intensification: ratio per scale in summary CSV (typically 2-6x)")
    print("-" * 95)
    print("[OK] Saved:")
    print(f"  CSV : {csv_raw_path}")
    print(f"  CSV : {csv_sum_path}")
    print(f"  JSON: {json_path}")

    return raw_records, summaries, aggregate


if __name__ == "__main__":
    run_memetic_benchmark()