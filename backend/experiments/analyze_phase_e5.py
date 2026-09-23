"""Analyze Phase E5 Fair Budget Benchmark Results."""

import json
import numpy as np

def analyze():
    with open("experiments/results/phase_e5_fair_budget_benchmark.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    scales = [5, 10, 15, 20, 30, 40, 50]

    print("\n" + "=" * 95)
    print("  PHASE E5 BENCHMARK: FAIR COMPUTATIONAL BUDGET & SCALABILITY ANALYSIS")
    print("=" * 95)

    print("\n1. COMPOSITE OBJECTIVE J (Dimensionless: 0.7*T/T_ref + 0.3*D/D_ref)")
    print(f"{'Scale':<6} | {'Greedy':<9} | {'ORT 100m':<9} | {'ORT 500m':<9} | {'ORT 2000m':<9} | {'QPSO P10':<9} | {'QPSO P20':<9} | {'QPSO P50':<9}")
    print("-" * 88)
    for s in scales:
        g = next(r["raw_objective"] for r in data if r["scale"] == s and r["solver"] == "Greedy_NN")
        o100 = next(r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_100ms")
        o500 = next(r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_500ms")
        o2000 = next(r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_2000ms")
        q10 = float(np.mean([r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P10_I15"]))
        q20 = float(np.mean([r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P20_I30"]))
        q50 = float(np.mean([r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P50_I100"]))
        print(f"{s:<6} | {g:<9.4f} | {o100:<9.4f} | {o500:<9.4f} | {o2000:<9.4f} | {q10:<9.4f} | {q20:<9.4f} | {q50:<9.4f}")

    print("\n2. ACTUAL RUNTIME (ms)")
    print(f"{'Scale':<6} | {'Greedy':<9} | {'ORT 100m':<9} | {'ORT 500m':<9} | {'ORT 2000m':<9} | {'QPSO P10':<9} | {'QPSO P20':<9} | {'QPSO P50':<9}")
    print("-" * 88)
    for s in scales:
        g = next(r["runtime_ms"] for r in data if r["scale"] == s and r["solver"] == "Greedy_NN")
        o100 = next(r["runtime_ms"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_100ms")
        o500 = next(r["runtime_ms"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_500ms")
        o2000 = next(r["runtime_ms"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_2000ms")
        q10 = float(np.mean([r["runtime_ms"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P10_I15"]))
        q20 = float(np.mean([r["runtime_ms"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P20_I30"]))
        q50 = float(np.mean([r["runtime_ms"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P50_I100"]))
        print(f"{s:<6} | {g:<9.2f} | {o100:<9.1f} | {o500:<9.1f} | {o2000:<9.1f} | {q10:<9.1f} | {q20:<9.1f} | {q50:<9.1f}")

    print("\n3. RELATIVE COST GAP VS OR-TOOLS 2-SECOND REFERENCE (%)")
    print(f"{'Scale':<6} | {'Greedy':<9} | {'ORT 100m':<9} | {'ORT 500m':<9} | {'QPSO P10':<9} | {'QPSO P20':<9} | {'QPSO P50':<9}")
    print("-" * 76)
    for s in scales:
        g = next(r["gap_vs_ortools_2s_ref_pct"] for r in data if r["scale"] == s and r["solver"] == "Greedy_NN")
        o100 = next(r["gap_vs_ortools_2s_ref_pct"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_100ms")
        o500 = next(r["gap_vs_ortools_2s_ref_pct"] for r in data if r["scale"] == s and r["budget_label"] == "ORT_500ms")
        q10 = float(np.mean([r["gap_vs_ortools_2s_ref_pct"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P10_I15"]))
        q20 = float(np.mean([r["gap_vs_ortools_2s_ref_pct"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P20_I30"]))
        q50 = float(np.mean([r["gap_vs_ortools_2s_ref_pct"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P50_I100"]))
        print(f"{s:<6} | {g:<+9.2f} | {o100:<+9.2f} | {o500:<+9.2f} | {q10:<+9.2f} | {q20:<+9.2f} | {q50:<+9.2f}")

    print("\n4. FEASIBILITY RATE")
    for s in scales:
        all_ort_feas = all(r["is_feasible"] for r in data if r["scale"] == s and "ORT" in r["budget_label"])
        all_qpso_feas = all(r["is_feasible"] for r in data if r["scale"] == s and "QPSO" in r["budget_label"])
        print(f"Scale {s:<2} ({s} customers): OR-Tools Feasibility: {all_ort_feas} | QPSO Feasibility: {all_qpso_feas}")

    print("\n5. QPSO MULTI-SEED VARIANCE (Across 3 seeds: 42, 101, 2024)")
    print(f"{'Scale':<6} | {'P10 Std':<10} | {'P20 Std':<10} | {'P50 Std':<10} | {'P50 Min J':<10} | {'P50 Max J':<10}")
    print("-" * 65)
    for s in scales:
        p10_costs = [r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P10_I15"]
        p20_costs = [r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P20_I30"]
        p50_costs = [r["raw_objective"] for r in data if r["scale"] == s and r["budget_label"] == "QPSO_P50_I100"]
        print(f"{s:<6} | {np.std(p10_costs):<10.4f} | {np.std(p20_costs):<10.4f} | {np.std(p50_costs):<10.4f} | {min(p50_costs):<10.4f} | {max(p50_costs):<10.4f}")

if __name__ == "__main__":
    analyze()
