import React, { useState, useEffect } from 'react';
import { OperationsView } from './components/operations/OperationsView';
import { FleetView } from './components/fleet/FleetView';
import { BenchmarkView } from './components/BenchmarkView';
import { QuantumInspector } from './components/QuantumInspector';
import {
  fetchNetwork,
  optimizeRoute,
  optimizeVRP,
  injectIncident,
  resetTraffic,
  fetchScenarios,
  fetchLandmarks,
  fetchSystemStatus,
  routeRealWorld,
  optimizeRealWorldVRP
} from './services/api';
import type {
  NetworkGeoJSON,
  OptimizeRouteResponse,
  VRPResponse,
  ScenarioPreset,
  Landmark,
  SystemStatus,
  RealWorldRouteResponse,
  RealWorldVRPResponse,
  FleetDepot,
  FleetStop,
  RealWorldVRPRequest,
  PlaceSearchResult
} from './types';
import {
  Map,
  Truck,
  BarChart3,
  Atom,
  Zap,
  RotateCcw,
  PlayCircle,
  Check,
  ChevronRight,
  ChevronLeft
} from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'operations' | 'fleet_vrp' | 'benchmark' | 'quantum'>('operations');
  const [network, setNetwork] = useState<NetworkGeoJSON | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioPreset[]>([]);

  // Real-World Routing State (OSM + OSRM Engine)
  const [landmarks, setLandmarks] = useState<Landmark[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [originLandmark, setOriginLandmark] = useState<string>('rk_beach');
  const [destLandmark, setDestLandmark] = useState<string>('rushikonda_beach');
  const [realWorldRoute, setRealWorldRoute] = useState<RealWorldRouteResponse | null>(null);
  const [routingMode, setRoutingMode] = useState<'realworld' | 'research'>('realworld');

  // Point-to-Point Curated Routing State (Research Mode)
  const [originNode, setOriginNode] = useState<string>('1');
  const [destinationNode, setDestinationNode] = useState<string>('6');
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>(['astar', 'qpso']);
  const [weights, setWeights] = useState<Record<string, number>>({
    time: 0.5,
    distance: 0.2,
    congestion: 0.2,
    emissions: 0.1
  });
  const [routeResults, setRouteResults] = useState<OptimizeRouteResponse | null>(null);

  // Fleet VRP State
  const [depotNode, setDepotNode] = useState<string>('4');
  const [numVehicles, setNumVehicles] = useState<number>(3);
  const [vehicleCapacity, setVehicleCapacity] = useState<number>(300.0);
  const [vrpResults, setVrpResults] = useState<VRPResponse | null>(null);
  const [realWorldVRPResult, setRealWorldVRPResult] = useState<RealWorldVRPResponse | null>(null);

  // Incident & UI State
  const [selectedEdge, setSelectedEdge] = useState<{ u: string; v: string } | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // SIH 5-Minute Guided Pitch Stepper State
  const [demoStep, setDemoStep] = useState<number | null>(null);

  const loadNetwork = async () => {
    try {
      const data = await fetchNetwork('visakhapatnam_network');
      setNetwork(data);
    } catch (e) {
      console.error('Failed to fetch road network:', e);
    }
  };

  const loadPresetScenarios = async () => {
    try {
      const sc = await fetchScenarios();
      setScenarios(sc);
    } catch (e) {
      console.error('Failed to load scenarios:', e);
    }
  };

  const handleRunRealWorldRoute = async (
    originId?: string,
    destId?: string,
    coords?: {
      originLat?: number;
      originLon?: number;
      destLat?: number;
      destLon?: number;
      originName?: string;
      destName?: string;
      originPlace?: PlaceSearchResult;
      destPlace?: PlaceSearchResult;
    }
  ) => {
    setIsLoading(true);
    try {
      if (coords?.originPlace && coords?.destPlace) {
        const res = await routeRealWorld({
          origin_lat: coords.originPlace.latitude,
          origin_lon: coords.originPlace.longitude,
          dest_lat: coords.destPlace.latitude,
          dest_lon: coords.destPlace.longitude,
          origin_name: coords.originPlace.name,
          dest_name: coords.destPlace.name,
          origin_place: coords.originPlace,
          dest_place: coords.destPlace,
          alternatives: true
        });
        setRealWorldRoute(res);
      } else if (coords?.originLat !== undefined && coords?.destLat !== undefined) {
        const res = await routeRealWorld({
          origin_lat: coords.originLat,
          origin_lon: coords.originLon,
          dest_lat: coords.destLat,
          dest_lon: coords.destLon,
          origin_name: coords.originName || 'Origin',
          dest_name: coords.destName || 'Destination',
          alternatives: true
        });
        setRealWorldRoute(res);
      } else {
        const orig = originId || originLandmark;
        const dest = destId || destLandmark;
        if (!orig || !dest) return;
        const res = await routeRealWorld({
          origin_id: orig,
          destination_id: dest,
          alternatives: true
        });
        setRealWorldRoute(res);
      }
    } catch (e) {
      console.error('Real-world route calculation error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadNetwork();
    loadPresetScenarios();

    const initRealWorld = async () => {
      try {
        const lmData = await fetchLandmarks();
        if (lmData?.landmarks) {
          setLandmarks(lmData.landmarks);
        }
        const stData = await fetchSystemStatus();
        if (stData) {
          setSystemStatus(stData);
        }
      } catch (err) {
        console.warn('Real-world routing initial fetch:', err);
      }
    };
    initRealWorld();
  }, []);

  const handleRunRealWorldVRP = async (
    depotId: string,
    customerIds: string[],
    numVehicles: number,
    capacity: number,
    customerDemands?: number[],
    depot?: FleetDepot,
    customers?: FleetStop[]
  ) => {
    setIsLoading(true);
    try {
      const payload: RealWorldVRPRequest = {
        num_vehicles: numVehicles,
        vehicle_capacity_kg: capacity
      };
      if (customers && customers.length > 0 && depot) {
        payload.depot = depot;
        payload.customers = customers;
      } else {
        payload.depot_id = depotId;
        payload.customer_ids = customerIds;
        payload.customer_demands = customerDemands || customerIds.map(() => 50.0);
      }
      const res = await optimizeRealWorldVRP(payload);
      setRealWorldVRPResult(res);
    } catch (e) {
      console.error('Real-world VRP optimization error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNodeSelect = (nodeId: string) => {
    if (activeTab === 'operations') {
      if (!originNode || (originNode && destinationNode)) {
        setOriginNode(nodeId);
        setDestinationNode('');
      } else {
        setDestinationNode(nodeId);
      }
    } else if (activeTab === 'fleet_vrp') {
      setDepotNode(nodeId);
    }
  };

  const handleEdgeSelect = (u: string, v: string) => {
    setSelectedEdge({ u, v });
  };

  const handleRunOptimization = async () => {
    if (!originNode || !destinationNode) return;
    setIsLoading(true);
    try {
      const res = await optimizeRoute({
        graph_id: 'visakhapatnam_network',
        origin_node: originNode,
        destination_node: destinationNode,
        algorithms: selectedAlgos,
        weights: weights
      });
      setRouteResults(res);
    } catch (e) {
      console.error('Optimization error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunVRP = async () => {
    setIsLoading(true);
    try {
      const res = await optimizeVRP({
        graph_id: 'visakhapatnam_network',
        depot_node: depotNode,
        num_vehicles: numVehicles,
        vehicle_capacity_kg: vehicleCapacity
      });
      setVrpResults(res);
    } catch (e) {
      console.error('VRP Optimization error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadScenario = async (scenario: ScenarioPreset) => {
    setIsLoading(true);
    try {
      await resetTraffic('visakhapatnam_network');
      for (const inc of scenario.incidents) {
        await injectIncident({
          graph_id: 'visakhapatnam_network',
          u: inc.u,
          v: inc.v,
          incident_type: inc.incident_type,
          multiplier: inc.multiplier,
          is_closed: inc.is_closed
        });
      }
      setOriginNode(scenario.origin_node);
      setDestinationNode(scenario.destination_node);
      await loadNetwork();
      const res = await optimizeRoute({
        graph_id: 'visakhapatnam_network',
        origin_node: scenario.origin_node,
        destination_node: scenario.destination_node,
        algorithms: selectedAlgos,
        weights: weights
      });
      setRouteResults(res);
    } catch (e) {
      console.error('Error applying scenario:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerEdgeIncident = async (type: string, multiplier: number, isClosed: boolean) => {
    if (!selectedEdge) return;
    setIsLoading(true);
    try {
      await injectIncident({
        graph_id: 'visakhapatnam_network',
        u: selectedEdge.u,
        v: selectedEdge.v,
        incident_type: type,
        multiplier: multiplier,
        is_closed: isClosed
      });
      await loadNetwork();
      if (routeResults) {
        await handleRunOptimization();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetDemo = async () => {
    setIsLoading(true);
    try {
      await resetTraffic('visakhapatnam_network');
      setSelectedEdge(null);
      setOriginNode('1');
      setDestinationNode('6');
      setDepotNode('4');
      setActiveTab('operations');
      setRouteResults(null);
      setVrpResults(null);
      setDemoStep(null);
      await loadNetwork();
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------------
  // SIH 5-Minute Guided Pitch Choreography
  // -------------------------------------------------------------
  const executeDemoStep = async (step: number) => {
    setDemoStep(step);
    setIsLoading(true);
    try {
      if (step === 1) {
        // Step 1: Normal Baseline Route (RK Beach to Rushikonda)
        setActiveTab('operations');
        await resetTraffic('visakhapatnam_network');
        setOriginNode('1');
        setDestinationNode('6');
        setSelectedAlgos(['astar', 'qpso']);
        await loadNetwork();
        const res = await optimizeRoute({
          graph_id: 'visakhapatnam_network',
          origin_node: '1',
          destination_node: '6',
          algorithms: ['astar', 'qpso'],
          weights: { time: 0.5, distance: 0.2, congestion: 0.2, emissions: 0.1 }
        });
        setRouteResults(res);
      } else if (step === 2) {
        // Step 2: Trigger Coastal Landslide Shock (5->6 Closed)
        setActiveTab('operations');
        await injectIncident({
          graph_id: 'visakhapatnam_network',
          u: '5',
          v: '6',
          incident_type: 'landslide_closure',
          multiplier: 1.0,
          is_closed: true
        });
        await loadNetwork();
      } else if (step === 3) {
        // Step 3: Run Dynamic Reroute (Diverts via Simhachalam Bypass)
        setActiveTab('operations');
        const res = await optimizeRoute({
          graph_id: 'visakhapatnam_network',
          origin_node: '1',
          destination_node: '6',
          algorithms: ['astar', 'qpso'],
          weights: { time: 0.5, distance: 0.2, congestion: 0.2, emissions: 0.1 }
        });
        setRouteResults(res);
      } else if (step === 4) {
        // Step 4: Multi-Vehicle Commercial Fleet VRP
        setActiveTab('fleet_vrp');
        setDepotNode('4');
        setNumVehicles(3);
        const res = await optimizeVRP({
          graph_id: 'visakhapatnam_network',
          depot_node: '4',
          num_vehicles: 3,
          vehicle_capacity_kg: 300.0
        });
        setVrpResults(res);
      } else if (step === 5) {
        // Step 5: Scientific Validation Dashboard
        setActiveTab('benchmark');
      } else if (step === 6) {
        // Step 6: QAOA Quantum Optimization Lab
        setActiveTab('quantum');
      }
    } catch (e) {
      console.error('Demo step execution error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const demoStepDescriptions = [
    {
      title: '1. Baseline Route',
      desc: 'Free-flow from RK Beach (1) to Rushikonda (6). Baseline A* and QPSO select Coastal Expressway (10.9m).'
    },
    {
      title: '2. Coastal Landslide',
      desc: 'Simulating coastal road closure (5 -> 6). Notice the red closure overlay on the Visakhapatnam map.'
    },
    {
      title: '3. QPSO Dynamic Reroute',
      desc: 'Optimizer detects blockage and diverts to Simhachalam Bypass corridor (23.9m) with 100% feasibility.'
    },
    {
      title: '4. Commercial Fleet VRP',
      desc: 'Dispatches 3 delivery trucks from Maddilapalem Hub across commercial stops under capacity limits.'
    },
    {
      title: '5. Scientific Validation',
      desc: '100% data-driven benchmarks: 0.00% exact VRP gap (N=4, 5, 6), paired scalability, and sensitivity.'
    },
    {
      title: '6. Quantum Optimization Lab',
      desc: 'Inspects QAOA quantum circuit synthesis and statevector probabilities for small QUBO formulations.'
    }
  ];

  return (
    <div className="flex flex-col h-screen w-screen bg-[#F8FAFC] text-slate-800 overflow-hidden font-sans">
      {/* ------------------------------------------------------------- */}
      {/* 1. CLEAN LIGHT HEADER */}
      {/* ------------------------------------------------------------- */}
      <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between z-20 shrink-0 shadow-sm">
        {/* Brand & Product Identity */}
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xs font-bold tracking-tight text-slate-900 uppercase">
                Visakhapatnam Intelligent Traffic
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-semibold flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                OSM Road Network
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">
              Traffic-Aware Navigation & Constrained Fleet Optimization
            </p>
          </div>
        </div>

        {/* 4 Standard Product Modes: Driver | Fleet | Research | Quantum Lab */}
        <nav aria-label="Product Modes" className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/80">
          <button
            onClick={() => setActiveTab('operations')}
            aria-label="Driver Mode"
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 ${
              activeTab === 'operations'
                ? 'bg-white text-blue-600 shadow-sm font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Map className="w-3.5 h-3.5" /> Driver
          </button>

          <button
            onClick={() => setActiveTab('fleet_vrp')}
            aria-label="Fleet Mode"
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 ${
              activeTab === 'fleet_vrp'
                ? 'bg-white text-emerald-600 shadow-sm font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Truck className="w-3.5 h-3.5" /> Fleet
          </button>

          <button
            onClick={() => setActiveTab('benchmark')}
            aria-label="Research Mode (Scientific Validation)"
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 ${
              activeTab === 'benchmark'
                ? 'bg-white text-purple-600 shadow-sm font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" /> Research
          </button>

          <button
            onClick={() => setActiveTab('quantum')}
            aria-label="Quantum Lab Mode"
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 ${
              activeTab === 'quantum'
                ? 'bg-white text-blue-600 shadow-sm font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Atom className="w-3.5 h-3.5" /> Quantum Lab
          </button>
        </nav>

        {/* Global Provenance Strip & Reset Demo Action */}
        <div className="flex items-center gap-2.5">
          <div className="hidden lg:flex items-center gap-3 bg-slate-50 border border-slate-200/90 px-2.5 py-1 rounded-lg text-[10px] font-medium text-slate-600">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              <span className="font-bold text-slate-400 uppercase text-[9px]">ROUTING</span>
              OSRM · Road Routing
            </span>
            <span className="text-slate-300">|</span>
            <span className="flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full ${
                realWorldRoute?.primary_route?.traffic_source?.includes('TOMTOM') || realWorldRoute?.primary_route?.traffic_freshness === 'LIVE' ? 'bg-emerald-500 animate-pulse' :
                realWorldRoute?.primary_route?.traffic_freshness === 'DEMO' ? 'bg-purple-500' : 'bg-slate-400'
              }`} />
              <span className="font-bold text-slate-400 uppercase text-[9px]">TRAFFIC</span>
              {realWorldRoute?.primary_route?.traffic_source?.includes('TOMTOM') || realWorldRoute?.primary_route?.traffic_freshness === 'LIVE'
                ? 'LIVE · TOMTOM'
                : realWorldRoute?.primary_route?.traffic_freshness === 'DEMO'
                ? 'DEMO · Controlled Shock'
                : 'UNAVAILABLE · LIVE TRAFFIC NOT AVAILABLE'}
            </span>
          </div>

          <button
            onClick={handleResetDemo}
            title="Reset All Incidents & Routing State"
            className="px-3 py-1 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 transition flex items-center gap-1.5 border border-slate-300 shadow-xs"
          >
            <RotateCcw className="w-3 h-3 text-amber-500" /> Reset Demo
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* 2. SLIM 1-ROW DEMO STEPPER TOOLBAR */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-1.5 flex items-center justify-between text-xs z-10 shrink-0">
        <div className="flex items-center gap-3">
          <span className="font-bold text-amber-700 text-[11px] flex items-center gap-1">
            <PlayCircle className="w-3.5 h-3.5 text-amber-600" />
            DEMO:
          </span>

          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5, 6].map((step) => (
              <button
                key={step}
                onClick={() => executeDemoStep(step)}
                disabled={isLoading}
                className={`px-2.5 py-0.5 rounded-lg text-[11px] transition flex items-center gap-1 ${
                  demoStep === step
                    ? 'bg-blue-600 text-white font-bold shadow-sm'
                    : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                }`}
              >
                {demoStep !== null && demoStep > step ? (
                  <Check className="w-2.5 h-2.5 text-emerald-600 font-bold" />
                ) : (
                  <span>{step}</span>
                )}
                <span>
                  {step === 1
                    ? 'Baseline'
                    : step === 2
                    ? 'Shock'
                    : step === 3
                    ? 'Reroute'
                    : step === 4
                    ? 'Fleet'
                    : step === 5
                    ? 'Validation'
                    : 'Quantum'}
                </span>
              </button>
            ))}
          </div>
        </div>

        {demoStep !== null && (
          <div className="text-slate-600 text-[11px] font-medium max-w-lg truncate hidden md:block">
            <span className="text-blue-700 font-bold">Step {demoStep}:</span>{' '}
            {demoStepDescriptions[demoStep - 1]?.desc}
          </div>
        )}

        <div className="flex items-center gap-1">
          <button
            onClick={() => executeDemoStep(Math.max(1, (demoStep || 1) - 1))}
            disabled={isLoading || demoStep === null || demoStep === 1}
            className="p-1 rounded bg-white border border-slate-200 hover:bg-slate-100 disabled:opacity-40 text-slate-600 shadow-sm"
          >
            <ChevronLeft className="w-3 h-3" />
          </button>
          <button
            onClick={() => executeDemoStep(demoStep === null ? 1 : Math.min(6, demoStep + 1))}
            disabled={isLoading || demoStep === 6}
            className="px-2.5 py-0.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold flex items-center gap-1 disabled:opacity-40 text-[11px] shadow-sm"
          >
            <span>{demoStep === null ? 'Start Demo' : 'Next'}</span>
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 3. MAIN PRODUCT CANVAS */}
      {/* ------------------------------------------------------------- */}
      <main className="flex-1 relative overflow-hidden">
        {activeTab === 'operations' && (
          <OperationsView
            network={network}
            originNode={originNode}
            destinationNode={destinationNode}
            setOriginNode={setOriginNode}
            setDestinationNode={setDestinationNode}
            selectedAlgos={selectedAlgos}
            setSelectedAlgos={setSelectedAlgos}
            weights={weights}
            setWeights={setWeights}
            scenarios={scenarios}
            onLoadScenario={handleLoadScenario}
            onRunOptimization={handleRunOptimization}
            onResetTraffic={handleResetDemo}
            isLoading={isLoading}
            selectedEdge={selectedEdge}
            onTriggerEdgeIncident={handleTriggerEdgeIncident}
            routeResults={routeResults}
            onSelectNode={handleNodeSelect}
            onSelectEdge={handleEdgeSelect}
            landmarks={landmarks}
            originLandmark={originLandmark}
            destinationLandmark={destLandmark}
            setOriginLandmark={setOriginLandmark}
            setDestinationLandmark={setDestLandmark}
            realWorldRoute={realWorldRoute}
            onRunRealWorldRoute={handleRunRealWorldRoute}
            routingMode={routingMode}
            setRoutingMode={setRoutingMode}
            systemStatus={systemStatus}
          />
        )}

        {activeTab === 'fleet_vrp' && (
          <FleetView
            network={network}
            depotNode={depotNode}
            setDepotNode={setDepotNode}
            numVehicles={numVehicles}
            setNumVehicles={setNumVehicles}
            vehicleCapacity={vehicleCapacity}
            setVehicleCapacity={setVehicleCapacity}
            onRunVRP={handleRunVRP}
            isLoading={isLoading}
            vrpResults={vrpResults}
            onSelectNode={handleNodeSelect}
            landmarks={landmarks}
            realWorldVRPResult={realWorldVRPResult}
            onRunRealWorldVRP={handleRunRealWorldVRP}
          />
        )}

        {activeTab === 'benchmark' && (
          <div className="h-full overflow-y-auto p-4 max-w-7xl mx-auto">
            <BenchmarkView />
          </div>
        )}

        {activeTab === 'quantum' && (
          <div className="h-full overflow-y-auto p-4 max-w-7xl mx-auto">
            <QuantumInspector />
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
