# SIH Technical Judge Defense & Pitch Guide (Empirical Validation Edition)

---

## 1. Top 10 High-Stakes Judge Attack Questions & Defensible Answers

### Q1: Does your system actually demonstrate dynamic rerouting when traffic changes, or does it just change edge numbers?
**Answer**:
Our system demonstrates **genuine dynamic route choice across alternative corridors**:
1. In our Visakhapatnam topology, there are multiple distinct arterial corridors connecting central hubs to major destinations like Rushikonda IT SEZ (`6`):
   - **Corridor 1 (Coastal Marine Drive Expressway)**: `1 (RK Beach) -> 13 -> 5 -> 6` (Normal: 10.93 min)
   - **Corridor 2 (BRTS Simhachalam / Health City Bypass)**: `1 -> 13 -> 4 -> 11 -> 6` (Normal: 23.90 min)
2. **Under Normal Free-Flow**: Both $A^*$ and QPSO select the Coastal Expressway (10.93 min).
3. **Under Landslide Shock (`5 -> 6` Closed)**: The optimizer dynamically detects the coastal closure and **reroutes via the Simhachalam Bypass (`1 -> 13 -> 4 -> 11 -> 6`)** with 100% feasibility (Route Overlap drops to 16.7%, Route Change is 83.3%).
4. **Under Port Freight Bottleneck (`9 -> 3` 3.5x Delay)**: The optimizer detects the bottleneck and **reroutes via Scindia / Gajuwaka (`9 -> 14 -> 8 -> 7`)** (Route Overlap is 0.0%, 100% Route Change).
5. **Under Total Destination Isolation**: When all inbound links to a destination are closed, the system correctly reports **`INFEASIBLE (No Route)`**.

---

### Q2: Did QPSO outperform Dijkstra or A*?
**Answer**:
**Not for conventional single-criterion point-to-point shortest paths.** Our point-to-point scalability benchmarks across 15 to 500 nodes demonstrate that specialized classical shortest-path algorithms like Dijkstra (~0.1 ms to ~7.3 ms) and $A^*$ (~0.1 ms to ~7.1 ms) are substantially faster than QPSO (~92 ms to ~430 ms). Dijkstra is a polynomial-time exact algorithm for single-source shortest path with non-negative additive weights.

Our QPSO research specifically targets **non-convex combinatorial and multi-objective problems**—such as Capacitated Vehicle Routing with Time Windows (CVRP+TW) and dynamic disruption shocks under non-linear BPR congestion latency—where the solution space is non-convex and NP-hard.

---

### Q3: How do you prove your Quantum-Inspired algorithm actually works? What is your optimality gap?
**Answer**:
We implemented an **Exact Exhaustive Reference Solver** (`ExactExhaustiveVRP`) to compute the exact optimum for bounded test instances ($N \le 6$) and evaluated 10 independent deterministic random seeds (`[42, 101, 7, 23, 88, 12, 99, 54, 31, 77]`):
- **$N=4$ Customer Stops**: Exact Optimum for Bounded Instance = 18.524. Greedy Gap = **+6.37%**, **Random-Key QPSO Gap = 0.00% (Matches Exact Optimum for Bounded Instance)**.
- **$N=5$ Customer Stops**: Exact Optimum for Bounded Instance = 27.806. Greedy Gap = **+4.24%**, **Random-Key QPSO Gap = 0.00% (Matches Exact Optimum for Bounded Instance)**.
- **$N=6$ Customer Stops**: Exact Optimum for Bounded Instance = 43.458. Greedy Gap = **+2.72%**, **Random-Key QPSO Gap = 0.00% (Matches Exact Optimum with 100% Feasibility)**.

---

### Q4: Why did QPSO become infeasible on the 500-node point-to-point test?
**Answer**:
Our scalability benchmark intentionally tested a **fixed search budget of 20 particles and 30 iterations** across all network scales ($N=15$ to $N=500$). In our dedicated **Single-Seed Parameter Sensitivity Study** ($P \in \{10, 20, 30, 50\} \times I \in \{15, 30, 50, 100\}$), we observed that:
- The baseline configuration ($P=20, I=30$) was infeasible.
- Scaling the search budget to ($P=50, I=100$, Cost = 71.257) restored feasibility and reduced objective cost by **52.6%** relative to ($P=20, I=15$, Cost = 150.422) and **36.8%** relative to ($P=10, I=30$, Cost = 112.729).
- Rather than hiding this search boundary, our Scientific Validation Dashboard transparently presents it as an **identified search budget boundary**.

---

### Q5: On VRP scalability (N=8, 12, 16), how did you handle infeasible trials?
**Answer**:
To maintain statistical integrity, we perform a **strictly paired statistical comparison**:
- We report the all-trial Greedy cost alongside the **paired Greedy cost computed exclusively on the feasible QPSO subset**.
- On $N=8$ stops (40% feasibility), QPSO achieved a **+5.86% objective cost reduction** compared to Greedy on the paired seeds.
- As problem scale increases ($N=12, 16$), feasibility under the default budget decays to 60% and 20%, clearly illustrating the combinatorial curse of dimensionality in fixed-budget swarm metaheuristics.

---

### Q6: What is your exact data provenance? Is this live traffic or OSM?
**Answer**:
- **Authoritative Road Network**: OpenStreetMap (OSM) highway vector topology via OSRM Contraction Hierarchies across 28 curated Visakhapatnam infrastructure landmarks.
- **Traffic & Incident Pipeline**: TomTom Traffic API adapter for real speed/jam observations when credentialed, integrated with the Bureau of Public Roads (BPR) non-linear latency physics equation ($\alpha=0.15, \beta=4.0$).
- **Demonstration Resilience**: Air-gapped local demo cache (`backend/transport/demo_cache.py`) for guaranteed offline presentations.
- **Quarantined Historical Benchmark**: 15-node dual-corridor network and synthetic planar graphs ($N=15 \dots 500$) isolated to the academic research laboratory.
- Every API response and UI component explicitly displays its auditable provenance tier tag (`REAL`, `DERIVED`, `SIMULATED`, `RESEARCH`).

---

### Q7: What is the difference between your QPSO and QAOA?
**Answer**:
- **QPSO (Quantum-Behaved Particle Swarm Optimization)**: A quantum-inspired classical metaheuristic operating on classical CPU hardware. It models particles bound in delta-potential quantum wells to achieve global search without velocity vectors.
- **QAOA (Quantum Approximate Optimization Algorithm)**: A gate-based quantum algorithm designed for NISQ quantum hardware. In our platform, QAOA is formulated as an Ising/QUBO Hamiltonian on a reduced 4-node problem, synthesized into OpenQASM 2.0 circuits, and simulated via NumPy/SciPy statevectors.

---

### Q8: What if the internet disconnects during the demo?
**Answer**:
The platform is architected with **multi-tiered offline resilience**:
1. In connected mode, it can route via live OSRM and ingest live TomTom Traffic API data.
2. If internet connectivity drops or during an air-gapped demo, the backend transparently falls back to its **local high-resolution demo cache** (`backend/transport/demo_cache.py`) with pre-computed OSRM route geometries and travel time matrices.
3. This air-gapped resilience is proven by our automated test suite (`TEST OFFLINE-DEMO-01`), which passes all 10 operational lifecycle steps with all non-loopback network sockets blocked.

---

### Q9: Can the user reset the system if an edge gets stuck in a broken state?
**Answer**:
Yes. We have provided a prominent **`Reset Demo`** button in the header and sidebar that instantly resets traffic incidents, restores the dual-corridor baseline, and resets all routing and VRP states in under 50 milliseconds.

---

### Q10: How many automated tests exist, and how are they run?
**Answer**:
The platform contains **115 automated pytest tests at the last local run (108 passed, 3 skipped, 4 offline network-dependent failures — see CI / re-run `pytest`, do not hardcode this number)** covering real-world OSM routing, BPR traffic data fusion, Google OR-Tools Guided Local Search vs QPSO, turn-by-turn step sum invariants, VRP capacity and customer partition invariants, deterministic QPSO reproducibility, the hard air-gapped offline demo lifecycle (`TEST OFFLINE-DEMO-01`), and QAOA circuit generation. When run with required dependencies installed (`pip install -r backend/requirements.txt`), the last local run collected **115 tests: 108 passed, 3 skipped, 4 offline network-dependent failures** (unmocked live TomTom Traffic API call correctly skipped when uncredentialed in an air-gapped environment; the failures require a live OSRM server). Run with: `cd backend && python -m pytest tests/ -v`.

---

## 2. The 5-Minute SIH Presentation & Pitch Choreography

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             5-MINUTE SIH PITCH CHOREOGRAPHY                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 0:00 - 0:45: PROBLEM & ARCHITECTURE                                                         │
│   • Show Visakhapatnam Command Center & Curated Geography Badge.                            │
│   • Problem: Urban coastal bottlenecking & logistics routing under stochastic disruptions.  │
│   • Core Architecture: Curated Geography -> BPR Dynamics -> Baselines -> QPSO & QAOA.      │
│                                                                                             │
│ 0:45 - 1:45: DUAL-CORRIDOR DYNAMIC ROUTING DEMO (Steps 1-3 in Pitch Stepper)                │
│   • Step 1: Run Baseline (RK Beach to Rushikonda IT SEZ via Coastal Marine Drive, 10.9m).   │
│   • Step 2: Trigger Coastal Landslide Shock (Road 5->6 closed).                             │
│   • Step 3: Run Dynamic QPSO Swarm -> Automatically diverts via Simhachalam Bypass (23.9m). │
│                                                                                             │
│ 1:45 - 2:45: COMMERCIAL FLEET VRP DISPATCH (Step 4 in Pitch Stepper)                        │
│   • Switch to Fleet VRP Mode: Dispatch 3 delivery trucks from Maddilapalem Hub.            │
│   • Demonstrate multi-vehicle route balancing under capacity and time windows.              │
│                                                                                             │
│ 2:45 - 4:00: EMPIRICAL SCIENTIFIC VALIDATION (Step 5 in Pitch Stepper)                      │
│   • Switch to Scientific Validation Tab.                                                    │
│   • Highlight Exact VRP Validation: 0.00% QPSO Gap across 10 random seeds on N=4, 5, 6.     │
│   • Highlight Dynamic Traffic Table: Diverted booleans & Jaccard overlap metrics.           │
│   • Highlight Parameter Sensitivity: Explaining the 500-node search budget boundary.        │
│                                                                                             │
│ 4:00 - 5:00: QUANTUM INSPECTOR & JUDGE Q&A (Step 6 in Pitch Stepper)                        │
│   • Switch to QAOA Inspector: Show OpenQASM 2.0 circuit and statevector probability.        │
│   • Deliver honest concluding slide: "What We Learned Experimentally".                      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```
