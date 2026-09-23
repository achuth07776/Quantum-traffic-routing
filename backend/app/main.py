import os
import json
from contextlib import asynccontextmanager

# Load local backend .env if present
def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v

_load_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.domain.graph import RoadGraph
from app.services.routing_service import RoutingService
from app.services.traffic_service import TrafficService
from app.services.quantum_service import QuantumService
from app.services.vrp_service import VRPService
from app.services.realworld_routing_service import RealWorldRoutingService
from transport.landmarks import LandmarkRegistry
from app.api.v1.routes import router, init_services

# Load default graphs on startup (legacy curated network for research mode)
def load_default_graphs():
    graphs = {}
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "graphs")
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(data_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    graph_id = data.get("graph_id", filename.replace(".json", ""))
                    graphs[graph_id] = RoadGraph.from_dict(data)
                except Exception as e:
                    print(f"Warning: Failed to load graph file '{filename}': {e}")
    return graphs

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    graphs = load_default_graphs()
    if not graphs:
        graphs["visakhapatnam_network"] = RoadGraph("visakhapatnam_network")

    # Legacy services (research mode, benchmarks, QAOA)
    traffic_svc = TrafficService(graphs)
    routing_svc = RoutingService(graphs)
    quantum_svc = QuantumService()
    vrp_svc = VRPService(graphs)

    # AUTHORITATIVE PRODUCTION ENGINE: Real-World OSM / OSRM Routing & Fleet VRP
    landmark_registry = LandmarkRegistry()
    realworld_routing_svc = RealWorldRoutingService(landmark_registry)

    print("[STARTUP] AUTHORITATIVE ENGINE: Real-World OSM Road Network & Constrained Fleet Optimizer")
    print(f"[STARTUP] Landmark Registry: {len(landmark_registry.get_all())} POIs loaded")
    print(f"[STARTUP] Active Routing Provider: {realworld_routing_svc._provider_name}")
    print(f"[STARTUP] RESEARCH BENCHMARK: {len(graphs)} historical graph(s) loaded for isolated paper validation")

    init_services(
        routing_svc, traffic_svc, quantum_svc, vrp_svc,
        realworld_routing_svc=realworld_routing_svc,
        landmark_reg=landmark_registry
    )
    yield
    # Shutdown

app = FastAPI(
    title="Visakhapatnam Intelligent Transportation Optimization Platform",
    description="Real-world traffic-aware routing and quantum-inspired fleet optimization for Visakhapatnam",
    version="3.0.0",
    lifespan=lifespan
)

# CORS Configuration: Restricted to local UI clients with environment override
allowed_origins_env = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
)
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
