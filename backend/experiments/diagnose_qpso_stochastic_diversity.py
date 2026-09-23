"""
Diagnostic: Stochastic Diversity Trace for Random-Key QPSO Across 10 Seeds.

Investigates:
1. Are initial particle positions and decoded permutations diverse across seeds?
2. How many unique candidate tours exist in the initial swarm (Iteration 0)?
3. How do particles traverse the search space across iterations (0 -> 10 -> 25 -> 50)?
4. Does the swarm start from different random states and converge along different trajectories?
"""

import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transport.landmarks import LandmarkRegistry
from transport.canonical_roads import CanonicalRoadRegistry, DataFusionEngine
from optimization.vrp.vrp_models import VRPProblem, CustomerStop
from optimization.vrp.matrix_vrp import MatrixVRPGraphHelper
from optimization.vrp.vrp_qpso import RandomKeyQPSOVRP
from providers.routing.osrm import OSRMRoutingProvider
from providers.routing.base import Coords
import asyncio


def run_diagnostic():
    print("=" * 80)
    print("QPSO STOCHASTIC DIVERSITY DIAGNOSTIC ACROSS 10 SEEDS")
    print("=" * 80)

    reg = LandmarkRegistry()
    osrm = OSRMRoutingProvider()
    depot_id = "maddilapalem_junction"
    customer_ids = ["rk_beach", "rushikonda_beach", "kailasagiri_hill", "nad_junction"]
    all_stop_ids = [depot_id] + customer_ids
    coords = [Coords(lat=reg.get_by_id(lid).lat, lon=reg.get_by_id(lid).lon) for lid in all_stop_ids]

    loop = asyncio.new_event_loop()
    table = loop.run_until_complete(osrm.table(coords))
    durations_t0 = [[round(s / 60.0, 2) for s in row] for row in table.durations_s]
    distances_t0 = [[round(m / 1000.0, 2) for m in row] for row in table.distances_m]

    customers = [
        CustomerStop(node_id=cid, name=cid, demand_kg=50.0, service_duration_min=0.0)
        for cid in customer_ids
    ]
    problem = VRPProblem(
        depot_node=depot_id,
        customers=customers,
        num_vehicles=2,
        vehicle_capacity_kg=300.0,
        max_route_time_min=300.0,
        population_size=40,
        max_iterations=50,
        weights={"time": 0.7, "distance": 0.3}
    )

    helper = MatrixVRPGraphHelper(
        node_ids=all_stop_ids,
        duration_matrix_min=durations_t0,
        distance_matrix_km=distances_t0,
        weights={"time": 0.7, "distance": 0.3},
        t_ref=11.96,
        d_ref=11.49
    )

    seeds = [42, 101, 7, 23, 88, 12, 99, 54, 31, 77]
    pop_size = 40
    num_cust = len(customers)
    max_iter = 50

    diagnostic_records = []

    for s in seeds:
        np.random.seed(s)
        # 1. Generate initial swarm
        initial_particles = np.random.uniform(-1.0, 1.0, (pop_size, num_cust))
        
        # Decode initial permutations
        initial_perms = set()
        for i in range(pop_size):
            perm = tuple(np.argsort(initial_particles[i]))
            initial_perms.add(perm)
        
        num_initial_unique_perms = len(initial_perms)

        # First particle's continuous position (showing different starting point in continuous space)
        first_particle_sample = [round(float(v), 3) for v in initial_particles[0]]

        # Run QPSO and monitor convergence
        qpso = RandomKeyQPSOVRP(num_particles=pop_size)
        problem.seed = s
        res = qpso.solve(graph=None, problem=problem, helper=helper)

        # Record trajectory snapshot
        conv = res.convergence_curve
        c_iter0 = conv[0] if len(conv) > 0 else res.total_cost
        c_iter10 = conv[9] if len(conv) > 9 else res.total_cost
        c_iter25 = conv[24] if len(conv) > 24 else res.total_cost
        c_final = conv[-1] if len(conv) > 0 else res.total_cost

        # Find iteration when global optimum (J <= 4.2470) was first discovered
        first_opt_iter = next((idx for idx, val in enumerate(conv) if round(val, 3) <= 4.247), len(conv) - 1)
        t_first_opt_ms = round(res.runtime_ms * ((first_opt_iter + 1) / max(1, len(conv))), 2)

        diagnostic_records.append({
            "Seed": s,
            "Initial_Particle_0_X": str(first_particle_sample),
            "Initial_Unique_Permutations": num_initial_unique_perms,
            "Total_Particles": pop_size,
            "J_Iter_0": round(c_iter0, 4),
            "First_Optimum_Iteration": first_opt_iter,
            "First_Optimum_Time_ms": t_first_opt_ms,
            "J_Iter_10": round(c_iter10, 4),
            "J_Iter_25": round(c_iter25, 4),
            "J_Final": round(c_final, 4),
            "Total_Runtime_ms": round(res.runtime_ms, 2),
            "Best_Route": " -> ".join(res.routes[0].customer_nodes)
        })

    df = pd.DataFrame(diagnostic_records)
    print("\nDIAGNOSTIC RESULTS:")
    print(df[["Seed", "Initial_Unique_Permutations", "J_Iter_0", "First_Optimum_Iteration", "First_Optimum_Time_ms", "J_Final", "Total_Runtime_ms"]].to_string(index=False))

    print("\nCONTINUOUS INITIAL VECTOR SAMPLE (Particle 0 across seeds):")
    for r in diagnostic_records:
        print(f"  Seed {r['Seed']:3d}: {r['Initial_Particle_0_X']}")

    out_csv = os.path.join(os.path.dirname(__file__), "results", "qpso_stochastic_diversity_diagnostic.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved diagnostic record to {out_csv}")


if __name__ == "__main__":
    run_diagnostic()
