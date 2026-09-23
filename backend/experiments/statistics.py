import numpy as np
from typing import List, Dict, Any

def compute_trial_statistics(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes rigorous statistical metrics across multiple random seeds/trials:
    Mean, Median, Min (Best), Max (Worst), Standard Deviation, Mean Runtime, Feasibility Rate.
    """
    if not runs:
        return {}
        
    costs = [r["total_fleet_cost"] for r in runs if r.get("is_feasible", False)]
    times = [r["total_fleet_time_min"] for r in runs if r.get("is_feasible", False)]
    runtimes = [r["runtime_ms"] for r in runs]
    feasibility_count = sum(1 for r in runs if r.get("is_feasible", False))
    total_runs = len(runs)
    
    # If no feasible runs, fallback
    if not costs:
        costs = [r.get("total_fleet_cost", float('inf')) for r in runs]
        times = [r.get("total_fleet_time_min", float('inf')) for r in runs]
        
    gaps = [r["optimality_gap_pct"] for r in runs if r.get("optimality_gap_pct") is not None]
    
    return {
        "num_trials": total_runs,
        "feasibility_rate_pct": round((feasibility_count / total_runs) * 100.0, 1),
        "mean_cost": round(float(np.mean(costs)), 3),
        "median_cost": round(float(np.median(costs)), 3),
        "best_cost": round(float(np.min(costs)), 3),
        "worst_cost": round(float(np.max(costs)), 3),
        "std_cost": round(float(np.std(costs)), 3),
        "mean_travel_time_min": round(float(np.mean(times)), 2),
        "mean_runtime_ms": round(float(np.mean(runtimes)), 2),
        "mean_optimality_gap_pct": round(float(np.mean(gaps)), 2) if gaps else None
    }
