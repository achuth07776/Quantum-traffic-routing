# Scientific Research Results & Empirical Validation Report

**Project**: Visakhapatnam Quantum-Inspired Intelligent Traffic Route & Fleet Optimization Platform  
**Evaluation Standard**: Smart India Hackathon (SIH) Research & Experimental Validation Framework  
**Data Version**: `final_results_v2.3`  
**Generated Artifacts**: `backend/data/experiments/final_results/` and `backend/data/experiments/plots/`

---

## 1. Experimental Setup & Hardware Environment

### Software & Hardware Specifications
- **Operating System**: Windows / Linux compatible (Cross-platform Python execution).
- **Runtime Environment**: Python 3.11+ / 3.14 with `numpy`, `scipy`, `networkx`, `fastapi`, `pydantic v2`, `ortools>=9.9.0`, `httpx>=0.27.0`, `pytest>=8.0.0`.
- **Plotting & Visualization Engine**: `matplotlib` 3.11+ (Headless Agg backend).
- **Frontend Architecture**: React 19.2.8 + TypeScript + Vite + Tailwind CSS + Leaflet (100% Data-Driven API Consumption).
- **Automated Test Suite**: **115 automated tests at the last local run** (**108 passed, 3 skipped, 4 offline network-dependent failures**; the failures require a live OSRM server — see CI / re-run `pytest`, do not hardcode this number). Execution requires `ortools` installed via `pip install -r backend/requirements.txt`.

### Random Seed Protocol
To eliminate stochastic sampling bias, all multi-trial metaheuristic experiments evaluate **10 independent deterministic random seeds**:
$$\text{Seeds} = [42, 101, 7, 23, 88, 12, 99, 54, 31, 77]$$

### Network Topology Tiers
1. **Visakhapatnam Curated Demonstration Graph**: 15 Nodes, 40 Directed Edges modeling real metropolitan landmarks, dual arterial corridors (Coastal Beach Road vs BRTS Simhachalam / Health City Bypass), and Port freight corridors.
2. **Synthetic Scalability Graph Tier**: Geometric k-nearest neighbor connected planar graphs generated at $N \in \{15, 50, 100, 250, 500\}$ nodes with non-linear BPR edge flow dynamics.

---

## 2. Master Summary of Findings

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            EMPIRICAL RESEARCH FINDINGS AT A GLANCE                          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. SMALL VRP OPTIMALITY GAP:                                                                │
│    Random-Key QPSO achieved a 0.00% Optimality Gap matching the Exact Exhaustive Reference  │
│    (the exact optimum for the bounded test instances N=4, 5, 6) across all 10 random seeds. │
│                                                                                             │
│ 2. DYNAMIC TRAFFIC REOPTIMIZATION:                                                          │
│    Under simulated road closure (Rushikonda Landslide) and port freight bottlenecks, QPSO   │
│    and baseline dynamically diverted routes to open bypass corridors with 100% feasibility. │
│                                                                                             │
│ 3. CLASSICAL POINT-TO-POINT SPEEDUP:                                                        │
│    Specialized classical algorithms (Dijkstra, A*) remained substantially faster (~0.1 ms   │
│    at 15 nodes to ~7.3 ms at 500 nodes) than QPSO (~92 ms to ~430 ms).                     │
│                                                                                             │
│ 4. SCALABILITY & SEARCH BUDGET BOUNDARY:                                                    │
│    Fixed search budgets (20p x 30i) exhibit feasibility degradation at 500 nodes / 16 VRP   │
│    stops. Single-seed parameter sweeps indicate that scaling budget restores feasibility.   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Experiment 1: Exact VRP Optimality Gap Validation

### Methodology
For small customer instances ($N=4, 5, 6$), the exact optimum for the bounded test instance $J^*$ is computed via `ExactExhaustiveVRP` (exhaustive permutation and vehicle partition enumeration). The Mean Optimality Gap is calculated as:
$$\text{Gap} = \frac{J_{\text{algorithm}} - J^*}{J^*} \times 100\%$$

### Measured Results (10 Seeds / Problem Size)
*Source: `backend/data/experiments/final_results/exact_vrp_summary.csv`*

| Problem Scale | Exact Optimum (Bounded Instance) | Exact Total Time | Greedy Mean Cost | Greedy Gap (%) | QPSO Mean Cost | QPSO Gap (%) | QPSO Feasibility | QPSO Mean Latency |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$N = 4$ Stops** | **18.524** | 64.07 min | 19.704 | **+6.37%** | **18.524** | **0.00% (Optimal)** | **100.0%** | 55.57 ms |
| **$N = 5$ Stops** | **27.806** | 85.75 min | 28.986 | **+4.24%** | **27.806** | **0.00% (Optimal)** | **100.0%** | 62.62 ms |
| **$N = 6$ Stops** | **43.458** | 122.44 min | 44.638 | **+2.72%** | **43.458** | **0.00% (Optimal)** | **100.0%** | 72.39 ms |

![Exact VRP Gap Plot](../backend/data/experiments/plots/exact_vrp_gap.png)

> **Defensible Claim**: On the tested $N=4, 5, 6$ VRP instances, exhaustive enumeration established the exact optimum for the bounded test instance, and Random-Key QPSO matched that optimum across all 10 tested seeds, while Greedy Nearest-Neighbor incurred sub-optimal gaps of 2.72% to 6.37%.

---

## 4. Experiment 2: Multi-Seed VRP Fleet Scalability (Paired Statistical Analysis)

### Methodology
Evaluated Capacitated VRP with Time Windows (CVRP+TW) on a 50-node synthetic network across $N=8, 12, 16$ customer stops over 10 independent random seeds. All hard constraints (vehicle payload capacity, max shift duration ceiling) were strictly enforced.

To maintain statistical integrity, **performance deltas are computed exclusively on paired trials where QPSO achieved feasibility**:
$$\text{Paired Cost Delta \%} = \frac{1}{|S_{\text{feas}}|} \sum_{k \in S_{\text{feas}}} \frac{J_{\text{Greedy}}^{(k)} - J_{\text{QPSO}}^{(k)}}{J_{\text{Greedy}}^{(k)}} \times 100\%$$

### Measured Results
*Source: `backend/data/experiments/final_results/vrp_scalability_summary.csv`*

| Problem Scale | Fleet Size | Greedy Cost (All Trials) | Greedy Cost (Paired Subset) | QPSO Cost (Feasible Subset) | Paired Cost $\Delta$ | Paired Time $\Delta$ | Runtime Ratio | Feasibility Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$N = 8$ Stops** | 2 Trucks | 33.128 | 35.421 | **33.253 (±1.06)** | **+5.86% (Better)** | +8.17% | 12.5x | **40.0% (4/10)** |
| **$N = 12$ Stops** | 3 Trucks | 46.836 | 50.699 | **52.783 (±4.08)** | **-4.66%** | +3.95% | 11.0x | **60.0% (6/10)** |
| **$N = 16$ Stops** | 4 Trucks | 68.672 | 72.621 | **73.824 (±1.44)** | **-1.66%** | +3.88% | 7.0x | **20.0% (2/10)** |

![VRP Feasibility vs Size](../backend/data/experiments/plots/vrp_feasibility_vs_size.png)
![VRP Runtime vs Size](../backend/data/experiments/plots/vrp_runtime_vs_size.png)

> **Defensible Claim**: Under the tested fixed search budget ($P=25, I=50$), QPSO feasibility decreased as problem scale increased. On the feasible subset for $N=8$, QPSO improved objective cost by 5.86% relative to Greedy on paired seeds, but scalability becomes budget-limited at larger fleet sizes.

---

## 5. Experiment 3: Dual-Corridor Dynamic Traffic Reoptimization

### Methodology
Evaluated route choice under 5 controlled traffic disruption scenarios on the Visakhapatnam dual-corridor network:
- **Corridor 1 (Coastal Route)**: `1 -> 13 -> 5 -> 6`
- **Corridor 2 (Simhachalam Bypass)**: `1 -> 13 -> 4 -> 11 -> 6`
- **Port Route**: `9 -> 3 -> 10 -> 7` vs `9 -> 14 -> 8 -> 7`

Edge-level Jaccard similarity and Route Change are tracked:
$$\text{RouteOverlap} = \frac{|E_{\text{pre}} \cap E_{\text{shock}}|}{|E_{\text{pre}} \cup E_{\text{shock}}|}, \quad \text{RouteChange} = 1 - \text{RouteOverlap}$$

### Measured Results
*Source: `backend/data/experiments/final_results/dynamic_traffic_summary.csv`*

| Scenario ID & Description | Pre-Shock Route (Time) | Post-Shock Baseline Route (Time) | Post-Shock QPSO Route (Time) | Route Diverted? | Route Overlap (Change) | Alternate Exists? | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **1. Normal Flow** | `1->13->5->6` (10.9m) | `1->13->5->6` (10.9m) | `1->13->5->6` (10.9m) | **NO (Optimal)** | 100.0% (0.0% Δ) | **YES** | **FEASIBLE** |
| **2. Rushikonda Landslide (`5->6` Closed)** | `1->13->5->6` (10.9m) | `1->13->4->11->6` (23.9m) | `1->13->4->11->6` (23.9m) | **YES (Diverted)** | 16.7% (83.3% Δ) | **YES** | **FEASIBLE** |
| **3. Maddilapalem Waterlogging (3.5x Delay)** | `1->13->5->6` (10.9m) | `1->13->5->6` (10.9m) | `1->13->5->6` (10.9m) | **NO (Direct)** | 100.0% (0.0% Δ) | **YES** | **FEASIBLE** |
| **4. Port Freight Spike (3.5x Delay)** | `9->3->10->7` (17.0m) | `9->14->8->7` (19.5m) | `9->14->8->7` (19.5m) | **YES (Diverted)** | 0.0% (100.0% Δ) | **YES** | **FEASIBLE** |
| **5. Total Destination Isolation** | `1->13->5->6` (10.9m) | `NO FEASIBLE ROUTE` ($\infty$) | `NO FEASIBLE ROUTE` ($\infty$) | **NO (Isolated)** | 0.0% (N/A) | **NO** | **INFEASIBLE** |

![Dynamic Route Change](../backend/data/experiments/plots/dynamic_route_change.png)

> **Defensible Claim**: Under simulated road closures and localized congestion spikes, the system re-evaluates network costs and dynamically diverts to an open alternative corridor when that corridor is preferable. When all inbound paths are blocked (Scenario 5), the system correctly reports infeasibility.

---

## 6. Experiment 4: Single-Seed QPSO Parameter Sensitivity (500-Node Network)

### Methodology
Evaluated 16 parameter grid configurations ($P \in \{10, 20, 30, 50\} \times I \in \{15, 30, 50, 100\}$) on a 500-node graph for Seed 42 to observe the trade-off between search budget, runtime, and feasibility.

### Measured Results
*Source: `backend/data/experiments/final_results/parameter_sensitivity_summary.csv`*

| Swarm Population ($P$) | Iterations ($I$) | Feasible? | Best Cost | Travel Time (min) | Runtime (ms) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 10 particles | 15 iters | **NO** | $\infty$ | $\infty$ | 111.91 ms |
| 10 particles | 30 iters | **YES** | 112.729 | 145.73 min | 251.68 ms |
| 10 particles | 50 iters | **YES** | 112.729 | 145.73 min | 404.70 ms |
| 10 particles | 100 iters | **YES** | 95.878 | 125.79 min | 786.02 ms |
| 20 particles | 15 iters | **YES** | 150.422 | 194.29 min | 243.42 ms |
| 20 particles | 30 iters | **NO** | $\infty$ | $\infty$ | 434.44 ms |
| 20 particles | 50 iters | **YES** | 125.241 | 163.30 min | 796.27 ms |
| 20 particles | 100 iters | **YES** | 87.781 | 113.65 min | 1608.94 ms |
| 30 particles | 15 iters | **NO** | $\infty$ | $\infty$ | 306.12 ms |
| 30 particles | 30 iters | **YES** | 289.120 | 378.70 min | 636.73 ms |
| 30 particles | 50 iters | **YES** | 84.559 | 108.79 min | 1006.41 ms |
| 30 particles | 100 iters | **YES** | 70.121 | 90.50 min | 2099.81 ms |
| 50 particles | 15 iters | **YES** | 74.513 | 97.00 min | 530.62 ms |
| 50 particles | 30 iters | **YES** | 74.513 | 97.00 min | 983.24 ms |
| 50 particles | 50 iters | **YES** | 74.513 | 97.00 min | 1629.23 ms |
| 50 particles | 100 iters | **YES** | **71.257** | 94.38 min | 3386.08 ms |

![Parameter Sensitivity Plot](../backend/data/experiments/plots/qpso_parameter_sensitivity.png)

> **Defensible Claim**: In this single-seed 500-node sensitivity study, the highest tested search budget ($P=50, I=100$, Cost = 71.257) improved objective cost by approximately **52.6%** relative to the low-budget feasible configuration ($P=20, I=15$, Cost = 150.422) and **36.8%** relative to ($P=10, I=30$, Cost = 112.729), while the baseline configuration ($P=20, I=30$) was infeasible. This indicates that feasibility and solution quality depend directly on allocating sufficient search budget for large topologies.

---

## 7. Experiment 5: Point-to-Point Routing Scalability

### Methodology
Benchmarked computation latency across network scales from 15 nodes (Visakhapatnam) up to 500 nodes.

### Measured Results
*Source: `backend/data/experiments/final_results/point_to_point_summary.csv`*

| Graph Scale | Edges | Dijkstra Runtime | $A^*$ Travel-Time Runtime | QPSO Runtime | QPSO Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **15 (Visakhapatnam)** | 40 | **0.126 ms** | **0.099 ms** (10.93m) | 92.45 ms | **FEASIBLE** |
| **50 Nodes** | 182 | **0.474 ms** | **0.400 ms** (15.79m) | 206.60 ms | **FEASIBLE** |
| **100 Nodes** | 356 | **1.514 ms** | **1.716 ms** (34.18m) | 293.35 ms | **FEASIBLE** |
| **250 Nodes** | 936 | **3.398 ms** | **3.215 ms** (43.26m) | 429.68 ms | **FEASIBLE** |
| **500 Nodes** | 1860 | **7.317 ms** | **7.105 ms** (67.57m) | 409.41 ms | **BUDGET LIMITED** |

![Point-to-Point Runtime Plot](../backend/data/experiments/plots/point_to_point_runtime.png)

> **Defensible Claim**: Dijkstra and $A^*$ remained substantially faster than QPSO across the entire 15–500 node range; classical runtimes scaled from ~0.10 ms at small scale to ~7.3 ms at 500 nodes, while QPSO required ~92 ms to ~430 ms. Classical algorithms are the appropriate tool for single-objective shortest paths.

---

## 8. Claims Supported by Evidence vs Claims NOT Supported

| Statement / Claim | Supported by Evidence? | Empirical Reason & Context |
| :--- | :---: | :--- |
| **"QPSO matches exact optimum on bounded VRP instances ($N \le 6$)"** | **YES** | Validated against exhaustive enumeration across 10 random seeds (0.00% Gap). |
| **"System dynamically reroutes when alternative corridors exist"** | **YES** | Validated on Coastal Landslide and Port freight scenarios. |
| **"System detects and reports network disconnection correctly"** | **YES** | Validated on Total Destination Isolation scenario. |
| **"QPSO is faster than Dijkstra for point-to-point routing"** | **NO** | Dijkstra is ~50x to 700x faster for single-criterion shortest paths. |
| **"System has achieved physical quantum advantage"** | **NO** | QPSO is a quantum-inspired classical algorithm; QAOA is simulated via statevectors. |
| **"Real OSM road network & OSRM routing engine"** | **YES** | Authoritative operational engine routes over real Visakhapatnam OpenStreetMap vectors across 28 curated landmarks; legacy 15-node graph is quarantined for historical benchmarks. |
| **"Traffic model predicts real live Visakhapatnam traffic"** | **QUALIFIED** | TomTom Traffic API adapter ingests real provider observations when credentialed; offline mode uses calibrated BPR link performance physics and controlled incident shocks. |

---

## 9. Reproducibility Instructions

To reproduce all 5 research experiments, regenerate all CSV summaries, update the statistical JSON, and regenerate all 7 publication plots, run from the repository root:

```bash
cd backend
python -m experiments.runner
```

To run the automated pytest test suite (115 tests at the last local run — see CI / re-run `pytest`, do not hardcode):

```bash
cd backend
python -m pytest tests/ -v
```

> **Note on Environment Dependencies**: Running the full backend test suite requires `ortools>=9.9.0` and `httpx>=0.27.0` (pinned in `backend/requirements.txt`). In an air-gapped test environment where pip cannot download binary wheels from PyPI, tests depending on `ortools` will fail collection unless the wheel is cached or pre-installed. When installed, the last local run collected **115 tests: 108 passed, 3 skipped, 4 offline network-dependent failures** (unmocked live TomTom Traffic API call correctly skipped when uncredentialed; the failures require a live OSRM server). See CI / re-run `pytest` for the current count — do not hardcode.
