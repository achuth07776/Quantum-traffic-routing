# System Architecture & Technical Specifications

## 1. Executive Summary
The **Visakhapatnam Intelligent Traffic Route & Fleet Optimization Platform** is a modular decision-support system designed to solve dynamic, multi-objective vehicle routing and fleet dispatch problems under stochastic traffic disruptions.

The architecture operates on an **authoritative real-world engine** for operational navigation and commercial fleet logistics, while isolating historical curated graphs into a **quarantined scientific benchmark laboratory**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│             PRESENTATION LAYER (React 19.2.8 + Vite + TS + Leaflet)    │
│  - Driver Navigation View: OpenStreetMap vectors, turn-by-turn guidance│
│  - Fleet VRP Dispatch View: Multi-vehicle routing, delay-avoided stats │
│  - Dual Route Map Overlay: Inaction Plan (Red) vs Reoptimized (Emerald)│
│  - Scientific Validation Dashboard: Bounded exact proofs & multi-seed  │
│  - OpenQASM 2.0 Circuit Inspector & 4-Qubit Statevector Visualizer     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                    API LAYER (FastAPI / Pydantic v2)                   │
│  - /api/v1/landmarks               - /api/v1/realworld/route           │
│  - /api/v1/realworld/matrix        - /api/v1/realworld/vrp             │
│  - /api/v1/traffic/snapshot        - /api/v1/traffic/incident          │
│  - /api/v1/benchmark/summary       - /api/v1/quantum/qaoa              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│               AUTHORITATIVE REAL-WORLD ROUTING & FLEET ENGINE          │
│  - RealWorldRoutingService: OpenStreetMap & OSRM Contraction Hierarchies│
│  - LandmarkRegistry: 28 Curated Visakhapatnam GPS POIs                 │
│  - CanonicalRoadRegistry: Physical arterial corridors (Beach Rd, NH16) │
│  - TrafficFusionEngine: TomTom Traffic API / synthetic flow + BPR physics │
│  - Fleet Solvers: Google OR-Tools (Guided Local Search) vs QPSO        │
│  - DemoCache: Air-gapped offline snapshot resilience (~2ms latency)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│            QUARANTINED RESEARCH & BENCHMARK SUITE (ISOLATED)           │
│  - Curated 15-Node Historical Graph (Isolated historical baseline)     │
│  - Synthetic Scalability Graph Generator (N=15 to N=500 planar graphs) │
│  - Exact Permutation Solver (Exact optimum for bounded N<=6 instances) │
│  - QAOA QUBO Variational Quantum Circuit Simulator (OpenQASM 2.0)      │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Core Modules
1. **Authoritative Real-World Routing (`backend/app/services/realworld_routing_service.py`)**:
   - Manages point-to-point road queries, $N \times N$ travel-time matrix generation, and landmark snapping over real OpenStreetMap geometry via OSRM Contraction Hierarchies.
   - Includes automatic zero-latency fallback to `backend/transport/demo_cache.py` for guaranteed air-gapped demonstration resilience.
2. **Traffic Physics & Ingestion Layer (`backend/transport/`)**:
   - `canonical_roads.py`: Tracks physical road segments, directionality, capacity, and Bureau of Public Roads (BPR) speed-flow curves.
   - `landmarks.py`: Coordinates and metadata for 28 real Visakhapatnam infrastructure points.
   - `provenance.py`: Strict data provenance auditing (`REAL`, `DERIVED`, `SIMULATED`, `RESEARCH`).
3. **External Provider Adapters (`backend/providers/`)**:
   - `routing/osrm.py`: OSRM HTTP client with robust fallback mechanisms.
   - `routing/ors.py`: OpenRouteService directions and matrix client.
   - `traffic/tomtom.py`: TomTom Traffic API flow and incident client.
4. **Optimization Core (`backend/optimization/`)**:
   - `vrp/vrp_ortools.py`: Google OR-Tools Guided Local Search and Tabu Search CVRPTW solver.
   - `vrp/matrix_vrp.py`: Random-Key QPSO operating on arbitrary distance/duration matrices.
   - `quantum_inspired/qpso.py`: Continuous QPSO delta-potential particle swarm optimizer.
   - `quantum_native/qaoa_qubo.py`: Variational quantum solver synthesizing OpenQASM 2.0 circuits.
   - `vrp/exact_vrp.py`: Exact branch-and-bound solver establishing the exact optimum for bounded test instances ($N \le 6$).
5. **Scientific Experimentation Framework (`backend/experiments/`)**:
   - `runner.py`: Multi-seed automated trial runner.
   - `statistics.py`: Rigorous metrics aggregator (Mean, Median, StdDev, Optimality Gap %, Feasibility %).
   - `synthetic_generator.py`: Benchmark graph generator for historical scalability experiments.
