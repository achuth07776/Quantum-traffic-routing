# Visakhapatnam Quantum-Inspired Intelligent Traffic & Fleet Optimization Platform

A production-grade, explainable urban mobility and fleet routing platform for the **Smart India Hackathon (SIH)**. It combines **OpenStreetMap (OSM) highway topology**, **OSRM routing and distance-matrix engines**, **TomTom search and traffic flow data**, **Bureau of Public Roads (BPR) traffic fusion**, **Quantum-behaved Particle Swarm Optimization (QPSO)**, and **Google OR-Tools Guided Local Search**.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.141-009688)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19.2.8-61DAFB)](https://react.dev)
[![Vite](https://img.shields.io/badge/Build-Vite_8-646CFF)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Styles-Tailwind_CSS_v4-38B2AC)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB)](https://python.org)
[![OR-Tools](https://img.shields.io/badge/Solver-Google_OR-Tools_9.15-4285F4)](https://developers.google.com/optimization)
[![Tests](https://img.shields.io/badge/Pytest-112_Passed-27ae60)](backend/tests)

---

## Key Highlights

1. **Real-world architecture**: Point-to-point routing and fleet VRP run over the real Visakhapatnam road network (OpenStreetMap), the OSRM routing engine, and segment-level TomTom live-traffic flow matching. Historical 15-node graph models are quarantined to isolated academic benchmark suites.
2. **Segment-level live traffic fusion**: Route geometries are split into physical road segments and matched against live TomTom flow speeds (T = sum of L_i / v_i), with length-weighted traffic-coverage percentages and anti-double-counting invariants.
3. **Multi-alternative route optimization**: Candidate OSRM paths are evaluated and the optimal route selected via `argmin T`, with speed sanity checks (5-110 km/h) and turn-by-turn step-sum conservation invariants (<= 0.5 m, <= 0.5 s).
4. **Demand-constrained fleet VRP**: Capacitated Vehicle Routing with Time Windows (CVRPTW) across arbitrary customer stops, with mandatory positive delivery demands (kg > 0), comparing Random-Key QPSO against the Google OR-Tools Guided Local Search baseline.
5. **Truthful provenance and error handling**: No synthetic demo caches, no artificial bypass injections. Provider errors propagate honestly, and every response is categorized into four provenance tiers (`REAL`, `DERIVED`, `SIMULATED`, `RESEARCH`).

---

## Four Unified Product Operating Modes

The frontend provides a single unified interface divided into four modes:

| Mode | Purpose |
| :--- | :--- |
| Driver Navigation | Point-to-point routing across the real OSM/OSRM network with TomTom traffic fusion. |
| Fleet VRP | CVRPTW dispatch comparing OR-Tools and Random-Key QPSO. |
| Research Benchmark | Exact optimality baselines on frozen academic topologies. |
| Quantum Lab | QAOA QUBO statevector simulation with OpenQASM 2.0 circuit export. |

### 1. Driver Navigation Mode (Point-to-Point)

- **Engine**: OpenStreetMap road network + OSRM routing engine + segment-level TomTom live-traffic flow matching.
- **Landmarks and search**: Dynamic TomTom Place Search across Visakhapatnam, plus 28 curated landmarks.
- **Alternative selection**: Candidate routes are ranked by `argmin T(route)`, with an interactive route switcher and a transparent `why_this_route` explanation.
- **Auditability**: Live speed sanity classification (`VALID` / `SUSPICIOUS`) and turn-by-turn step-sum conservation verification.

### 2. Fleet Management Mode (CVRPTW Dispatch)

- **Engine**: Real-world N x N travel-time and distance matrices computed across arbitrary customer stops and depots.
- **Mandatory demands**: Each customer requires a positive delivery demand (kg > 0) to enforce genuine capacity constraints.
- **Solvers**:
  - **Google OR-Tools**: Guided Local Search metaheuristic baseline.
  - **Random-Key QPSO**: Delta-potential quantum-well particle swarm with capacity and time-window decoders.
- **Route-duration constraint**: `max_route_time_min` is enforced inside both solvers (OR-Tools receives it as a `RouteDuration` dimension), so infeasible instances are never reported as feasible.
- **Dynamic reoptimization**: Simulates real-time fleet rebalancing when major delivery arterials experience traffic shocks, quantifying delay avoided by re-routing.

### 3. Research Benchmark Mode (Optimality Verification)

- **Scope**: Quarantined scientific evaluation on frozen benchmark topologies.
- **Exact optimality proof**: An exact brute-force permutation solver (N! = 24 for 4 customers) confirms QPSO's optimality gap and feasibility rates.
- **Statistical significance**: Multi-seed reproducibility across seeds 42, 100, 2024, 777, 999 confirms stochastic-swarm convergence.

### 4. Quantum Lab Mode (QAOA Circuit Synthesis)

- **Engine**: 4-qubit Max-Cut / QUBO variational eigensolver using full statevector simulation.
- **Portability**: Interactive variational angle sliders (gamma, beta) with real-time **OpenQASM 2.0** circuit generation, ready for IBM Quantum or Qiskit backends.

---

## Data Provenance Architecture

All system data flows are categorized into four transparent tiers:

| Classification | Applied Scope | Description |
| :--- | :--- | :--- |
| `REAL` | Road topology and distances | OpenStreetMap highway geometry and OSRM matrix calculations. |
| `DERIVED` | Congestion and latencies | Physical travel times from the extended Bureau of Public Roads (BPR) equation: t = t0 [1 + alpha (V/C)^beta]. |
| `SIMULATED` | Incident shocks | Controlled corridor shocks (e.g. Beach Road, 1.0x to 3.0x multiplier) for live demonstration. |
| `RESEARCH` | Historical and quantum | Quarantined 15-node graph benchmarks and 4-qubit QAOA statevector simulation. |

Note: TomTom-dependent endpoints (`/search/places`, `/geocoding/forward`) strictly degrade when `TOMTOM_API_KEY` is not configured - `/search/places` returns an empty list and `/geocoding/forward` returns 404 rather than fabricating data.

---

## Launch Instructions

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API base: `http://localhost:8000`
- Interactive API docs (Swagger): `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- Web UI: `http://localhost:5173`

---

## Automated Verification

### Backend test suite

```bash
cd backend
python -m pytest -q
```

Last measured full run: **112 passed, 3 skipped, 0 failed** in ~142 s. The suite covers routing adapters, TomTom segment matching, OR-Tools VRP solvers (including budget clamping and route-duration infeasibility), QPSO reproducibility, and step-sum conservation invariants.

### Frontend production build

```bash
cd frontend
npm ci
npm run build
```

### End-to-end tests (Playwright)

```bash
cd frontend
npx playwright test
```

### Routing accuracy reference metrics

Evaluated against an independent navigation reference (Google Maps urban baseline) on `backend/data/validation_dataset.json`:

| Metric Category | Measure | Value |
| :--- | :--- | :--- |
| Distance | MAE | 0.29 km (1.54% MAPE) |
| ETA / Travel Time | MAE | 13.4 min (34.43% MAPE) |
| Average Speed | MAE | 15.05 km/h (51.92% MAPE) |
| Traffic Coverage | Length-weighted coverage | 23.1% of Visakhapatnam street length matched to live TomTom flow |
| Numerical Invariants | Step distance / duration conservation | 0.0 m / 0.0 s error (100% within tolerance) |
| Operational Quality | Speed sanity | 100% of routes within 5.0-110.0 km/h |
| Fleet Optimization | CVRPTW feasibility rate | 100.0% |

> Note: Google Maps is an external navigation reference, not ground truth.

---

## Packaging for SIH Submission

```bash
python scripts/package_submission.py
```

Produces a submission ZIP with verified file integrity, excluding `node_modules`, `.venv`, `__pycache__`, and other system-dependent files.

---

## Repository Structure

```text
backend/
  app/
    api/v1/routes.py          REST API endpoints (health, route, matrix, fleet, benchmarks)
    main.py                   FastAPI application setup, CORS, startup
    services/                 Real-world routing, fleet optimization, baseline services
  providers/
    routing/                  OSRM and OpenRouteService routing adapters
    traffic/tomtom.py         TomTom segment-level flow matching and incident adapter
    search/tomtom.py          TomTom dynamic place search provider
  transport/
    landmarks.py              28 curated Visakhapatnam POIs with coordinates
    canonical_roads.py        Canonical corridors, BPR latency curves, traffic fusion engine
    provenance.py             Data provenance tracking and metadata tagging
  optimization/
    quantum_inspired/qpso.py  Quantum-behaved Particle Swarm Optimization (QPSO)
    vrp/                      CVRPTW models, decoders, OR-Tools baseline, exact brute-force
    quantum_native/           QAOA/QUBO solver and OpenQASM 2.0 circuit generator
  requirements.txt            Core production dependencies
  requirements-dev.txt        Development and test dependencies
  tests/                      Unit, invariant, and integration test modules

frontend/
  src/
    components/               Driver navigation, fleet dispatch, benchmark, quantum views
    services/api.ts           TypeScript API client
    types/index.ts            TypeScript domain models
    App.tsx                   Main shell and mode navigation
  tests/e2e/                  Playwright end-to-end tests

scripts/
  build_validation_dataset.py
  debug_corridor_resolution.py
  package_submission.py
  trace_corridors.py
  verify_proofs.py

docs/                         In-depth architecture and algorithm documentation
```

---

## License and Intellectual Property

Developed for the **Smart India Hackathon (SIH)**. No license file is committed to this repository yet; unless a LICENSE is added, all rights are reserved. Contact the repository maintainers before reusing any code, algorithms, or data.