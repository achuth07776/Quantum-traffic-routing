# Mathematical Models & Algorithm Specifications

## 1. Bureau of Public Roads (BPR) Dynamic Travel Time
The link travel time $T_e$ in minutes on edge $e = (u, v)$ is modeled using the civil engineering standard BPR formulation:
$$T_e(F_e) = \left(\frac{L_e}{V_{\text{free}, e}}\right) \times 60 \times \left[ 1 + \alpha \left(\frac{F_e}{C_e}\right)^\beta \right] \times I_e$$
Where:
- $L_e$: Road segment length (km).
- $V_{\text{free}, e}$: Free-flow speed limit (km/h).
- $F_e$: Current vehicle flow (vehicles/hour).
- $C_e$: Practical road capacity (vehicles/hour).
- $\alpha = 0.15, \beta = 4.0$: Standard fixed calibration parameters.
- $I_e \ge 1.0$: Dynamic incident multiplier ($I_e = \infty$ for blocked roads).

---

## 2. Multi-Objective Cost Formulation
The composite cost of path $\pi = [v_1, v_2, \dots, v_k]$ is:
$$J(\pi) = w_1 \cdot \sum_{e \in \pi} T_e + w_2 \cdot \sum_{e \in \pi} (0.8 \cdot L_e) + w_3 \cdot \sum_{e \in \pi} 5 \left(\frac{F_e}{C_e}\right)^2 + w_4 \cdot \sum_{e \in \pi} \frac{\text{Emissions}_e}{200}$$
Subject to:
- $\forall e \in \pi, I_e < \infty$ (Hard constraint: zero traversal of closed road segments).
- Degree conservation at all intermediate nodes (Contiguous path validity).

---

## 3. Quantum-Behaved Particle Swarm Optimization (QPSO)
In QPSO, the state of particle $i$ is described by a wave function $\psi(X, t)$ in a quantum delta-potential well.
The Mean Best position $mbest$ of the swarm is:
$$mbest(t) = \frac{1}{M} \sum_{i=1}^M P_{\text{best}, i}(t)$$
The Local Quantum Attractor $P_i$ is:
$$P_i(t) = \phi \cdot P_{\text{best}, i}(t) + (1 - \phi) \cdot G_{\text{best}}(t), \quad \phi \sim U(0, 1)$$
The Position Update equation via wave-function collapse is:
$$X_i(t+1) = P_i(t) \pm \beta \cdot |mbest(t) - X_i(t)| \cdot \ln\left(\frac{1}{u}\right), \quad u \sim U(0, 1)$$
Where $\beta$ is the Contraction-Expansion (CE) coefficient dynamically decreasing linearly from $1.0$ to $0.5$ across iterations.

---

## 4. Capacitated VRP (CVRP+TW) & Constraint Decoding
- **Encoding**: Continuous vector $X_i \in [-1.0, 1.0]^N$ where $N$ is the number of customer delivery stops.
- **Random-Key Decoder**: Sorted indices of $X_i$ provide the visitation sequence. Customers are partitioned into vehicle routes strictly enforcing:
  1. **Hard Capacity Constraint**: $\sum_{c \in \text{Route}_k} \text{Demand}_c \le \text{Capacity}_k$.
  2. **Hard Route Duration Ceiling**: $\text{TotalTime}_k + \text{ReturnTime}_{\text{depot}} \le \text{MaxRouteTime}$.
  3. **Soft Time Window Constraint**: Lateness is penalized:
     $$P_{\text{TW}} = \sum \max(0, \text{Arrival}_c - \text{TimeWindowEnd}_c) \times \lambda_{\text{TW}}$$

### Google OR-Tools Reference Solver (`ortools_vrp.py`)
The classical reference solver (Google OR-Tools Guided Local Search) enforces the same constraints natively as OR-Tools routing *dimensions* over the travel-time matrix `duration_matrix_min` (minutes):
- **Capacity dimension** — `AddDimensionWithVehicleCapacity(demand_callback, 0, int_capacities, True, "Capacity")`: cumulative load starts at 0 with zero slack, and each vehicle's cumulative demand may not exceed its vehicle capacity.
- **Route-duration dimension** — `AddDimension(duration_callback, 0, int(round(max_route_time_min * DURATION_SCALE)), True, "RouteDuration")`, where `duration_callback` reads `duration_matrix_min` and `DURATION_SCALE = 1000` (minutes → integer, sub-second precision): cumulative per-vehicle travel time starts at 0, has zero slack, and may not exceed `max_route_time_min`.
- **Arc-cost objective** — the normalized composite cost $J = w_t \cdot (T/T_{\text{ref}}) + w_d \cdot (D/D_{\text{ref}})$ is scaled by $\text{SCALE} = 10^5$ and registered as the arc-cost evaluator for every vehicle (`SetArcCostEvaluatorOfAllVehicles`).

---

## 5. Exact Optimality Gap Formulation
For small VRP instances ($N \le 6$), the global minimum $J_{\text{exact}}^*$ is computed via exhaustive branch-and-bound permutation enumeration (`ExactExhaustiveVRP`).
The Optimality Gap for any algorithm is calculated as:
$$\text{Gap}_{\text{algo}} = \frac{J_{\text{algo}} - J_{\text{exact}}^*}{J_{\text{exact}}^*} \times 100\%$$
- Verified empirical result across 10 independent random seeds on Visakhapatnam network (`exact_vrp_summary.csv`):
  - $N=4$: Greedy Gap = +6.37%, **QPSO matched the exact optimum on the bounded benchmark, yielding a 0.00% optimality gap.**
  - $N=5$: Greedy Gap = +4.24%, **QPSO matched the exact optimum on the bounded benchmark, yielding a 0.00% optimality gap.**
  - $N=6$: Greedy Gap = +2.72% (sub-optimal), **QPSO matched the exact optimum on the bounded benchmark, yielding a 0.00% optimality gap (100% Feasibility).**
