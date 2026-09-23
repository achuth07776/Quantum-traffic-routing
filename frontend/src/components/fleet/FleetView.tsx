import React, { useState, useEffect } from 'react';
import { MapView } from '../MapView';
import {
  Truck,
  CheckCircle2,
  Play,
  Award,
  AlertTriangle,
  Search,
  Plus,
  Trash2,
  X
} from 'lucide-react';
import { trafficReoptimizeFleet, searchPlaces } from '../../services/api';
import type {
  NetworkGeoJSON,
  VRPResponse,
  GeoJSONFeature,
  VehicleRouteData,
  Landmark,
  RealWorldVRPResponse,
  FleetReoptimizationResponse,
  PlaceSearchResult,
  FleetStop,
  FleetDepot
} from '../../types';

interface FleetViewProps {
  network: NetworkGeoJSON | null;
  depotNode: string;
  setDepotNode: (id: string) => void;
  numVehicles: number;
  setNumVehicles: (n: number) => void;
  vehicleCapacity: number;
  setVehicleCapacity: (c: number) => void;
  onRunVRP: () => void;
  isLoading: boolean;
  vrpResults: VRPResponse | null;
  onSelectNode: (nodeId: string) => void;
  // Real-World Matrix & OR-Tools props
  landmarks?: Landmark[];
  realWorldVRPResult?: RealWorldVRPResponse | null;
  onRunRealWorldVRP?: (
    depotId: string,
    customerIds: string[],
    numVehicles: number,
    capacity: number,
    customerDemands?: number[],
    depot?: FleetDepot,
    customers?: FleetStop[]
  ) => void;
}

export const FleetView: React.FC<FleetViewProps> = ({
  network,
  depotNode,
  setDepotNode,
  numVehicles,
  setNumVehicles,
  vehicleCapacity,
  setVehicleCapacity,
  onRunVRP,
  isLoading,
  vrpResults,
  onSelectNode,
  landmarks = [],
  realWorldVRPResult,
  onRunRealWorldVRP
}) => {
  const [fleetMode, setFleetMode] = useState<'realworld' | 'research'>('realworld');
  const [realDepotId, setRealDepotId] = useState<string>('maddilapalem_junction');
  const [selectedCustomers, setSelectedCustomers] = useState<string[]>([
    'rk_beach',
    'rushikonda_beach',
    'nad_junction',
    'visakhapatnam_port',
    'kailasagiri_hill'
  ]);

  // Delivery demands per landmark stop (default 50.0 kg each)
  const [customerDemands, setCustomerDemands] = useState<Record<string, number>>({
    'rk_beach': 50.0,
    'rushikonda_beach': 60.0,
    'nad_junction': 40.0,
    'visakhapatnam_port': 75.0,
    'kailasagiri_hill': 45.0
  });

  // Custom searched stops
  const [customStops, setCustomStops] = useState<FleetStop[]>([]);
  const [stopSearchQuery, setStopSearchQuery] = useState('');
  const [stopSearchResults, setStopSearchResults] = useState<PlaceSearchResult[]>([]);
  const [isSearchingStop, setIsSearchingStop] = useState(false);
  const [showStopDropdown, setShowStopDropdown] = useState(false);

  // Debounced search for adding custom stop
  useEffect(() => {
    const q = stopSearchQuery.trim();
    if (!q || q.length < 2) {
      setStopSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearchingStop(true);
      try {
        const res = await searchPlaces(q, 6);
        setStopSearchResults(res);
      } catch (e) {
        console.error('Stop search error:', e);
      } finally {
        setIsSearchingStop(false);
      }
    }, 280);
    return () => clearTimeout(timer);
  }, [stopSearchQuery]);

  const handleAddSearchedStop = (place: PlaceSearchResult) => {
    const newStop: FleetStop = {
      id: place.id || `custom_${Date.now()}`,
      name: place.name,
      lat: place.latitude,
      lon: place.longitude,
      demand_kg: 50.0
    };
    setCustomStops((prev) => [...prev, newStop]);
    setStopSearchQuery('');
    setShowStopDropdown(false);
  };

  const handleRemoveCustomStop = (index: number) => {
    setCustomStops((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateCustomDemand = (index: number, val: number) => {
    setCustomStops((prev) =>
      prev.map((s, i) => (i === index ? { ...s, demand_kg: Math.max(1, val) } : s))
    );
  };

  const handleUpdateLandmarkDemand = (id: string, val: number) => {
    setCustomerDemands((prev) => ({
      ...prev,
      [id]: Math.max(1, val)
    }));
  };

  const nodes = network
    ? network.features
        .filter((f: GeoJSONFeature) => f.properties.type === 'node')
        .map((f: GeoJSONFeature) => ({ id: f.properties.id || '', name: f.properties.name || '' }))
    : [];

  const handleToggleCustomer = (id: string) => {
    if (selectedCustomers.includes(id)) {
      if (selectedCustomers.length + customStops.length > 2) {
        setSelectedCustomers(selectedCustomers.filter((cid) => cid !== id));
      }
    } else {
      setSelectedCustomers([...selectedCustomers, id]);
      if (!customerDemands[id]) {
        setCustomerDemands((prev) => ({ ...prev, [id]: 50.0 }));
      }
    }
  };

  const [trafficMode, setTrafficMode] = useState<'baseline' | 'shock'>('baseline');
  const [reoptResult, setReoptResult] = useState<FleetReoptimizationResponse | null>(null);
  const [isReoptimizing, setIsReoptimizing] = useState<boolean>(false);
  const [serviceDurationMin, setServiceDurationMin] = useState<number>(0);
  const [routeViewMode, setRouteViewMode] = useState<'both' | 'previous' | 'reoptimized'>('both');

  const handleTrafficReoptimization = async (shockActive: boolean) => {
    setTrafficMode(shockActive ? 'shock' : 'baseline');
    setIsReoptimizing(true);
    try {
      const demands = selectedCustomers.map((cid) => Math.max(1.0, customerDemands[cid] || 50.0));
      const res = await trafficReoptimizeFleet({
        depot_id: realDepotId,
        customer_ids: selectedCustomers,
        num_vehicles: numVehicles,
        vehicle_capacity_kg: vehicleCapacity,
        customer_demands: demands,
        target_corridor_id: 'beach_road',
        simulated_incident_multiplier: shockActive ? 3.0 : 1.0,
        simulated_closed: false
      });
      setReoptResult(res);
    } catch (err) {
      console.error('Fleet reoptimization failed:', err);
    } finally {
      setIsReoptimizing(false);
    }
  };

  const handleDispatchRealWorld = () => {
    if (!onRunRealWorldVRP) return;

    const depotLm = landmarks.find((l) => l.id === realDepotId);
    const depot: FleetDepot = depotLm
      ? { id: depotLm.id, name: depotLm.name, lat: depotLm.lat, lon: depotLm.lon }
      : { id: 'maddilapalem_junction', name: 'Maddilapalem Junction', lat: 17.7348, lon: 83.3245 };

    if (customStops.length > 0) {
      const landmarkStops: FleetStop[] = [];
      for (const cid of selectedCustomers) {
        const lm = landmarks.find((l) => l.id === cid);
        if (lm) {
          landmarkStops.push({
            id: lm.id,
            name: lm.name,
            lat: lm.lat,
            lon: lm.lon,
            demand_kg: customerDemands[cid] || 50.0
          });
        }
      }

      const allCustomers = [...landmarkStops, ...customStops];
      onRunRealWorldVRP(
        realDepotId,
        allCustomers.map((c) => c.id || c.name),
        numVehicles,
        vehicleCapacity,
        allCustomers.map((c) => c.demand_kg),
        depot,
        allCustomers
      );
    } else {
      const demands = selectedCustomers.map((cid) => Math.max(1.0, customerDemands[cid] || 50.0));
      onRunRealWorldVRP(
        realDepotId,
        selectedCustomers,
        numVehicles,
        vehicleCapacity,
        demands
      );
    }
  };

  return (
    <div className="relative w-full h-full overflow-hidden bg-slate-100 font-sans">
      {/* 1. FULL CANVAS MAP */}
      <div className="absolute inset-0 z-0">
        <MapView
          network={network}
          originNode=""
          destinationNode=""
          depotNode={depotNode}
          mode="fleet_vrp"
          onSelectNode={onSelectNode}
          onSelectEdge={() => {}}
          routeResults={null}
          vrpResults={vrpResults}
          activeAlgos={['qpso']}
          realWorldVRPResult={realWorldVRPResult}
          routeViewMode={routeViewMode}
        />
      </div>

      {/* 2. FLOATING LEFT FLEET CONTROL PANEL */}
      <div className="absolute top-4 left-4 z-10 w-84 max-w-[calc(100vw-2rem)] bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-2xl shadow-xl p-4 flex flex-col gap-3 text-slate-800 max-h-[calc(100vh-120px)] overflow-y-auto">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
              <Truck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-bold text-sm text-slate-900">Fleet Dispatch</h2>
              <p className="text-[10px] text-slate-500">Capacitated Multi-Vehicle VRP</p>
            </div>
          </div>

          {/* Mode Pill Toggle */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-[10px]">
            <button
              onClick={() => setFleetMode('realworld')}
              className={`px-2 py-0.5 rounded-md font-bold transition ${
                fleetMode === 'realworld'
                  ? 'bg-white text-emerald-700 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              OSRM Matrix
            </button>
            <button
              onClick={() => setFleetMode('research')}
              className={`px-2 py-0.5 rounded-md font-bold transition ${
                fleetMode === 'research'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Lab Graph
            </button>
          </div>
        </div>

        {fleetMode === 'realworld' ? (
          /* REAL ROAD NETWORK (OSRM TABLE) CONTROLS */
          <div className="space-y-3">
            {/* Real Depot Landmark Selector */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-600 flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-amber-500" /> Central Fleet Depot
                </span>
                <span className="text-[9px] text-slate-400 font-mono">28 Vizag Landmarks</span>
              </label>
              <select
                value={realDepotId}
                onChange={(e) => setRealDepotId(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:border-emerald-500 truncate shadow-xs"
              >
                {landmarks.map((lm) => (
                  <option key={lm.id} value={lm.id}>
                    {lm.name} ({lm.category})
                  </option>
                ))}
              </select>
            </div>

            {/* Dynamic Place Search to Add Stops */}
            <div className="relative space-y-1">
              <label className="text-[11px] font-semibold text-slate-600 flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <Search className="w-3 h-3 text-emerald-600" /> Search & Add Custom Stop
                </span>
                <span className="text-[9px] text-slate-400">TomTom Place Search</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={stopSearchQuery}
                  onChange={(e) => {
                    setStopSearchQuery(e.target.value);
                    setShowStopDropdown(true);
                  }}
                  onFocus={() => setShowStopDropdown(true)}
                  placeholder="Search address, store, hospital to add..."
                  className="w-full bg-white border border-slate-200 rounded-lg pl-2.5 pr-6 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:border-emerald-500 shadow-xs"
                />
                {isSearchingStop ? (
                  <div className="absolute right-2 top-2 w-3 h-3 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                ) : stopSearchQuery ? (
                  <button
                    type="button"
                    onClick={() => {
                      setStopSearchQuery('');
                      setShowStopDropdown(false);
                    }}
                    className="absolute right-1.5 top-1.5 text-slate-400 hover:text-slate-600 p-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                ) : (
                  <Search className="absolute right-2 top-2 w-3 h-3 text-slate-400 pointer-events-none" />
                )}
              </div>

              {/* Autocomplete Dropdown */}
              {showStopDropdown && stopSearchResults.length > 0 && (
                <div className="absolute left-0 right-0 mt-1 max-h-44 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-lg z-50 divide-y divide-slate-100">
                  {stopSearchResults.map((place) => (
                    <button
                      key={place.id}
                      type="button"
                      onClick={() => handleAddSearchedStop(place)}
                      className="w-full text-left px-3 py-2 hover:bg-emerald-50 transition flex items-start justify-between gap-2 text-xs"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-slate-900 truncate">{place.name}</div>
                        <div className="text-[10px] text-slate-500 truncate">{place.address}</div>
                      </div>
                      <span className="shrink-0 text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded flex items-center gap-0.5">
                        <Plus className="w-2.5 h-2.5" /> Add
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Custom Added Stops List */}
            {customStops.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">
                  Added Custom Stops ({customStops.length})
                </span>
                <div className="space-y-1 max-h-28 overflow-y-auto bg-emerald-50/50 p-2 rounded-xl border border-emerald-200/60 text-xs">
                  {customStops.map((stop, idx) => (
                    <div key={idx} className="flex items-center justify-between gap-1 p-1.5 bg-white rounded-lg border border-emerald-100 shadow-2xs">
                      <div className="min-w-0 flex-1 truncate font-medium text-slate-800 text-[11px]">
                        {stop.name}
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <input
                          type="number"
                          min="1"
                          max={vehicleCapacity}
                          value={stop.demand_kg}
                          onChange={(e) => handleUpdateCustomDemand(idx, parseFloat(e.target.value) || 1)}
                          className="w-12 px-1 py-0.5 text-[10px] text-right border border-slate-200 rounded font-mono font-semibold"
                        />
                        <span className="text-[9px] text-slate-500">kg</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveCustomStop(idx)}
                          className="p-1 text-slate-400 hover:text-red-600 rounded hover:bg-red-50"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Delivery Customer Stops Selection */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-semibold text-slate-600">Customer Delivery Stops & Demands</span>
                <span className="text-[10px] text-emerald-700 font-bold">
                  {selectedCustomers.length + customStops.length} Stops Active
                </span>
              </div>
              <div className="max-h-36 overflow-y-auto space-y-1 bg-slate-50 p-2 rounded-xl border border-slate-200/80 text-[11px]">
                {landmarks
                  .filter((lm) => lm.id !== realDepotId)
                  .map((lm) => {
                    const isChecked = selectedCustomers.includes(lm.id);
                    return (
                      <div
                        key={lm.id}
                        className={`flex items-center justify-between gap-2 p-1.5 rounded-lg transition ${
                          isChecked ? 'bg-white font-semibold text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        <label className="flex items-center gap-2 cursor-pointer min-w-0 flex-1">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleToggleCustomer(lm.id)}
                            className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                          />
                          <span className="truncate">{lm.name}</span>
                        </label>
                        {isChecked && (
                          <div className="flex items-center gap-1 shrink-0">
                            <input
                              type="number"
                              min="1"
                              max={vehicleCapacity}
                              value={customerDemands[lm.id] || 50}
                              onChange={(e) => handleUpdateLandmarkDemand(lm.id, parseFloat(e.target.value) || 1)}
                              className="w-12 px-1 py-0.5 text-[10px] text-right border border-slate-200 rounded font-mono font-semibold"
                            />
                            <span className="text-[9px] text-slate-400">kg</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* Fleet Size & Capacity */}
            <div className="space-y-2 bg-slate-50 p-2.5 rounded-xl border border-slate-200/80">
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-600 font-medium">Fleet Size</span>
                  <span className="text-emerald-700 font-bold font-mono">{numVehicles} Vehicles</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="4"
                  step="1"
                  value={numVehicles}
                  onChange={(e) => setNumVehicles(parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-600 font-medium">Payload Capacity</span>
                  <span className="text-emerald-700 font-bold font-mono">{vehicleCapacity} kg</span>
                </div>
                <input
                  type="range"
                  min="150"
                  max="500"
                  step="25"
                  value={vehicleCapacity}
                  onChange={(e) => setVehicleCapacity(parseFloat(e.target.value))}
                  className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
              </div>

              {/* Stop Service Time Selector (Transit vs Commercial Schedule) */}
              <div className="pt-2 border-t border-slate-200/70 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600 font-medium">Customer Service Duration</span>
                  <span className="text-emerald-700 font-bold font-mono">
                    {serviceDurationMin === 0 ? '0 min (Transit)' : `${serviceDurationMin} min (Delivery)`}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[10px]">
                  <button
                    type="button"
                    onClick={() => setServiceDurationMin(0)}
                    className={`py-1 px-1.5 rounded-lg font-semibold transition text-center ${
                      serviceDurationMin === 0
                        ? 'bg-emerald-600 text-white font-bold shadow-2xs'
                        : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    0m (Pure Transit)
                  </button>
                  <button
                    type="button"
                    onClick={() => setServiceDurationMin(5)}
                    className={`py-1 px-1.5 rounded-lg font-semibold transition text-center ${
                      serviceDurationMin === 5
                        ? 'bg-emerald-600 text-white font-bold shadow-2xs'
                        : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    5m (Commercial Dwell)
                  </button>
                </div>
              </div>
            </div>

            {/* Real-World System Provenance Panel */}
            <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-2.5 space-y-1.5 text-[10px]">
              <div className="flex items-center justify-between text-slate-700 font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span className="font-bold text-slate-500 uppercase text-[9px]">MATRIX:</span>
                  OSRM Table
                </span>
                <span className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${trafficMode === 'shock' ? 'bg-amber-500 animate-pulse' : 'bg-blue-500'}`} />
                  <span className="font-bold text-slate-500 uppercase text-[9px]">TRAFFIC:</span>
                  {trafficMode === 'shock' ? 'DEMO · 3.0x Delay' : 'BASELINE · Free-Flow'}
                </span>
              </div>
              <div className="flex items-center justify-between text-slate-700 font-medium pt-1 border-t border-slate-200/60">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                  <span className="font-bold text-slate-500 uppercase text-[9px]">CUSTOMERS:</span>
                  Operator-Configured (Real Roads)
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  <span className="font-bold text-slate-500 uppercase text-[9px]">VEHICLES:</span>
                  {numVehicles} ({vehicleCapacity}kg cap)
                </span>
              </div>
            </div>

            {/* Live Traffic Scenario Reoptimization Selector */}
            <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-2.5 space-y-2 text-xs">
              <div className="flex items-center justify-between font-bold text-amber-950 text-[11px]">
                <span className="flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  Live Fleet Reoptimization
                </span>
                <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 bg-amber-200/60 rounded text-amber-800">
                  {trafficMode === 'shock' ? 'T₁: Shock Active' : 'T₀: Free-Flow'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                <button
                  type="button"
                  onClick={() => handleTrafficReoptimization(false)}
                  disabled={isReoptimizing}
                  className={`py-1.5 px-2 rounded-lg font-semibold border transition text-center ${
                    trafficMode === 'baseline'
                      ? 'bg-white border-emerald-500 text-emerald-800 shadow-2xs font-bold'
                      : 'bg-amber-100/50 border-amber-200 text-amber-800 hover:bg-white'
                  }`}
                >
                  {isReoptimizing && trafficMode === 'baseline' ? 'Solving...' : 'Baseline (T₀)'}
                </button>
                <button
                  type="button"
                  onClick={() => handleTrafficReoptimization(true)}
                  disabled={isReoptimizing}
                  className={`py-1.5 px-2 rounded-lg font-semibold border transition text-center ${
                    trafficMode === 'shock'
                      ? 'bg-amber-600 text-white border-amber-700 shadow-2xs font-bold'
                      : 'bg-amber-100/50 border-amber-200 text-amber-800 hover:bg-white'
                  }`}
                >
                  {isReoptimizing && trafficMode === 'shock' ? 'Solving...' : 'Beach Rd Shock (T₁)'}
                </button>
              </div>
            </div>

            {/* CTA Button */}
            <button
              onClick={handleDispatchRealWorld}
              disabled={isLoading || isReoptimizing}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-md transition flex items-center justify-center gap-2 text-xs disabled:opacity-50"
            >
              {isLoading ? (
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-white" />
              )}
              <span>{isLoading ? 'Solving Road Matrix...' : 'Dispatch Fleet (OR-Tools vs QPSO)'}</span>
            </button>
          </div>
        ) : (
          /* LEGACY RESEARCH GRAPH CONTROLS */
          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-600 flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-amber-500" /> Curated Network Depot
              </label>
              <select
                value={depotNode}
                onChange={(e) => setDepotNode(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:border-emerald-500"
              >
                {nodes.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.name} (Node {n.id})
                  </option>
                ))}
              </select>
            </div>

            {/* Fleet Size & Capacity Parameters */}
            <div className="space-y-2 bg-slate-50 p-2.5 rounded-xl border border-slate-200/80">
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-600 font-medium">Fleet Size</span>
                  <span className="text-emerald-700 font-bold font-mono">{numVehicles} Trucks</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="4"
                  step="1"
                  value={numVehicles}
                  onChange={(e) => setNumVehicles(parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-600 font-medium">Payload Capacity</span>
                  <span className="text-emerald-700 font-bold font-mono">{vehicleCapacity} kg</span>
                </div>
                <input
                  type="range"
                  min="150"
                  max="500"
                  step="25"
                  value={vehicleCapacity}
                  onChange={(e) => setVehicleCapacity(parseFloat(e.target.value))}
                  className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
              </div>
            </div>

            {/* Primary CTA */}
            <button
              onClick={onRunVRP}
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-md transition flex items-center justify-center gap-2 text-xs disabled:opacity-50"
            >
              {isLoading ? (
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-white" />
              )}
              <span>{isLoading ? 'Optimizing Fleet...' : 'Dispatch Fleet (QPSO)'}</span>
            </button>
          </div>
        )}
      </div>

      {/* 3. FLOATING RIGHT FLEET RESULTS PANEL */}
      <div className="absolute top-4 right-4 z-10 w-92 max-w-[calc(100vw-2rem)] bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-2xl shadow-xl p-4 flex flex-col gap-3 text-slate-800 max-h-[calc(100vh-120px)] overflow-y-auto">
        <div className="flex items-center justify-between pb-1 border-b border-slate-100">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Fleet Telemetry</span>
          {(realWorldVRPResult || vrpResults) && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Feasible Schedule
            </span>
          )}
        </div>

        {/* Hero Dynamic Fleet Reoptimization Alert Card */}
        {reoptResult && (
          <div className="bg-amber-50/90 border-2 border-amber-300 rounded-2xl p-3.5 space-y-3 text-amber-950 shadow-md">
            {/* Dominant Alert Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
                <span className="font-extrabold text-xs uppercase tracking-wide text-red-900">
                  TRAFFIC SHOCK DETECTED
                </span>
              </div>
              <span className="text-[9px] font-mono font-bold bg-amber-200/80 px-2 py-0.5 rounded-full text-amber-950 uppercase">
                {reoptResult.traffic_condition}
              </span>
            </div>

            {/* Inaction vs Reoptimized Times */}
            <div className="bg-white/95 p-3 rounded-xl border border-amber-200/90 shadow-2xs space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-600 font-medium">Previous plan under current traffic:</span>
                <span className="font-mono font-bold text-red-600">
                  {reoptResult.value_of_reoptimization.ortools.shocked_old_plan_time_min} min
                  {reoptResult.value_of_reoptimization.ortools.shocked_old_plan_distance_km ? ` · ${reoptResult.value_of_reoptimization.ortools.shocked_old_plan_distance_km} km` : ''}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-600 font-medium">Reoptimized plan:</span>
                <span className="font-mono font-bold text-emerald-600">
                  {reoptResult.value_of_reoptimization.ortools.reoptimized_time_min} min
                  {reoptResult.value_of_reoptimization.ortools.reoptimized_distance_km ? ` · ${reoptResult.value_of_reoptimization.ortools.reoptimized_distance_km} km` : ''}
                </span>
              </div>

              {/* Dominant Hero Metric: Congestion Delay Avoided */}
              <div className="pt-2 border-t border-slate-100 flex items-baseline justify-between">
                <div>
                  <div className="text-3xl font-black text-emerald-600 tracking-tight">
                    {reoptResult.value_of_reoptimization.ortools.time_saved_by_reoptimization_min}{' '}
                    <span className="text-sm font-bold text-emerald-700">min</span>
                  </div>
                  <span className="text-[10px] font-extrabold text-emerald-800 uppercase tracking-wide block">
                    Congestion Delay Avoided
                  </span>
                </div>
                <div className="text-right">
                  <span className="inline-block px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-800 font-extrabold text-xs shadow-2xs">
                    {reoptResult.value_of_reoptimization.ortools.pct_delay_reduction ?? (reoptResult.value_of_reoptimization.ortools.shocked_old_plan_time_min > 0 ? ((reoptResult.value_of_reoptimization.ortools.time_saved_by_reoptimization_min / reoptResult.value_of_reoptimization.ortools.shocked_old_plan_time_min) * 100).toFixed(1) : '0.0')}% reduction
                  </span>
                </div>
              </div>
            </div>

            {/* Decision Trade-Off Callout */}
            <div className="bg-emerald-50/80 border border-emerald-200/90 rounded-xl p-2.5 text-xs text-emerald-950 space-y-0.5">
              <span className="font-bold text-emerald-900 block text-[10px] uppercase tracking-wide">
                Decision Trade-Off
              </span>
              <p className="text-slate-700 font-medium leading-relaxed text-[11px]">
                <b>+{reoptResult.value_of_reoptimization.ortools.distance_added_km ?? 0} km</b> distance traded for <b>-{reoptResult.value_of_reoptimization.ortools.time_saved_by_reoptimization_min} min</b> congestion delay. Reoptimized fleet circumvents {reoptResult.corridor_targeted || 'congested corridor'} via arterial bypass.
              </p>
            </div>

            {/* Map View Toggle Buttons */}
            <div className="flex items-center gap-1 bg-amber-100/60 p-1 rounded-xl border border-amber-200/70">
              <button
                type="button"
                onClick={() => setRouteViewMode('both')}
                className={`flex-1 py-1 px-1.5 rounded-lg text-[10px] font-bold transition text-center ${
                  routeViewMode === 'both'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-amber-900 hover:bg-amber-100'
                }`}
              >
                [ SHOW BOTH ]
              </button>
              <button
                type="button"
                onClick={() => setRouteViewMode('previous')}
                className={`flex-1 py-1 px-1.5 rounded-lg text-[10px] font-bold transition text-center ${
                  routeViewMode === 'previous'
                    ? 'bg-red-600 text-white shadow-xs'
                    : 'text-amber-900 hover:bg-amber-100'
                }`}
              >
                [ PREVIOUS ]
              </button>
              <button
                type="button"
                onClick={() => setRouteViewMode('reoptimized')}
                className={`flex-1 py-1 px-1.5 rounded-lg text-[10px] font-bold transition text-center ${
                  routeViewMode === 'reoptimized'
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-amber-900 hover:bg-amber-100'
                }`}
              >
                [ REOPTIMIZED ]
              </button>
            </div>

            {/* Service Dwell Adjustment Breakdown (if enabled) */}
            {serviceDurationMin > 0 && (() => {
              const numStops = selectedCustomers.length;
              const totalDwell = numStops * serviceDurationMin;
              const totalShift = reoptResult.value_of_reoptimization.ortools.reoptimized_time_min + totalDwell;
              return (
                <div className="bg-slate-100 p-2 rounded-lg text-[10px] text-slate-700 space-y-0.5 font-mono border border-slate-200">
                  <span className="font-bold block text-slate-800 font-sans">Operational Schedule Breakdown:</span>
                  <div>Road Transit: <b>{reoptResult.value_of_reoptimization.ortools.reoptimized_time_min} min</b></div>
                  <div>Customer Dwell: <b>{numStops} stops × {serviceDurationMin} min = {totalDwell.toFixed(1)} min</b></div>
                  <div className="text-emerald-700 font-bold border-t border-slate-200 pt-0.5">
                    Total Shift Duration: {totalShift.toFixed(1)} min
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* Real-World VRP Comparison Telemetry */}
        {fleetMode === 'realworld' && realWorldVRPResult && realWorldVRPResult.status === 'SUCCESS' ? (
          <div className="space-y-3">
            {/* Hero Benchmark Comparison Card */}
            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-700 uppercase flex items-center gap-1">
                  <Award className="w-3.5 h-3.5 text-amber-500" />
                  Real-Network VRP Benchmark
                </span>
                <span className="text-[10px] font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200 shadow-2xs">
                  Ref Cost Gap: {realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct !== undefined && realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct !== null
                    ? `${realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct > 0 ? '+' : ''}${realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct}%`
                    : (realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct !== null && realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct !== undefined
                      ? `${realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct > 0 ? '+' : ''}${realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct}%`
                      : '0.00%')}
                </span>
              </div>

              {/* Explicit Normalized Objective Definition Box */}
              <div className="bg-blue-50/60 border border-blue-100 rounded-lg p-2 text-[10px] space-y-1 text-blue-950">
                <div className="flex justify-between font-semibold">
                  <span>Normalized Objective:</span>
                  <span className="font-mono">J = 0.7·(T/T_ref) + 0.3·(D/D_ref)</span>
                </div>
                {realWorldVRPResult.benchmark_comparison.objective_function?.reference_scales && (
                  <div className="flex items-center gap-2 text-[9px] font-mono text-blue-800 bg-white/80 p-1 rounded border border-blue-100/60">
                    <span>T_ref: {realWorldVRPResult.benchmark_comparison.objective_function.reference_scales.t_ref_min} min</span>
                    <span>·</span>
                    <span>D_ref: {realWorldVRPResult.benchmark_comparison.objective_function.reference_scales.d_ref_km} km</span>
                  </div>
                )}
                <p className="text-[9px] text-blue-700 leading-tight">
                  Normalized dimensionless scales ensure calibrated 70% time / 30% distance weighting across all three solvers.
                </p>
              </div>

              {/* Head-to-Head Comparison Table */}
              <div className="border border-slate-200 rounded-lg overflow-hidden bg-white text-[11px]">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 text-[10px] text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="p-1.5">Solver</th>
                      <th className="p-1.5 font-mono" title="Dimensionless composite objective">Composite Obj (J)</th>
                      <th className="p-1.5">Fleet Time</th>
                      <th className="p-1.5">Distance</th>
                      <th className="p-1.5">Compute</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="bg-blue-50/30 text-blue-900 font-semibold">
                      <td className="p-1.5 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                        OR-Tools (Ref)
                      </td>
                      <td className="p-1.5 font-mono text-blue-800">
                        {realWorldVRPResult.results.ortools.total_fleet_cost}
                      </td>
                      <td className="p-1.5">{realWorldVRPResult.results.ortools.total_fleet_time_min}m</td>
                      <td className="p-1.5">{realWorldVRPResult.results.ortools.total_fleet_distance_km}km</td>
                      <td className="p-1.5 text-slate-500">{realWorldVRPResult.results.ortools.runtime_ms}ms</td>
                    </tr>
                    <tr className="bg-emerald-50/40 text-emerald-900 font-semibold">
                      <td className="p-1.5 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                        QPSO (Swarm)
                      </td>
                      <td className="p-1.5 font-mono text-emerald-800">
                        {realWorldVRPResult.results.qpso.total_fleet_cost}
                      </td>
                      <td className="p-1.5">{realWorldVRPResult.results.qpso.total_fleet_time_min}m</td>
                      <td className="p-1.5">{realWorldVRPResult.results.qpso.total_fleet_distance_km}km</td>
                      <td className="p-1.5 text-slate-500">{realWorldVRPResult.results.qpso.runtime_ms}ms</td>
                    </tr>
                    <tr className="text-slate-600">
                      <td className="p-1.5 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                        Greedy (NN)
                      </td>
                      <td className="p-1.5 font-mono">
                        {realWorldVRPResult.results.greedy.total_fleet_cost}
                      </td>
                      <td className="p-1.5">{realWorldVRPResult.results.greedy.total_fleet_time_min}m</td>
                      <td className="p-1.5">{realWorldVRPResult.results.greedy.total_fleet_distance_km}km</td>
                      <td className="p-1.5 text-slate-500">{realWorldVRPResult.results.greedy.runtime_ms}ms</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Multi-Metric Gap Breakdown */}
              <div className="grid grid-cols-3 gap-1 text-center text-[10px]">
                <div className="bg-white border border-slate-200 p-1 rounded">
                  <span className="text-[9px] text-slate-400 block uppercase">Cost Gap vs Ref</span>
                  <span className="font-bold text-slate-800 font-mono">
                    {realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct !== undefined && realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct !== null
                      ? `${realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct > 0 ? '+' : ''}${realWorldVRPResult.benchmark_comparison.qpso_cost_gap_vs_reference_pct}%`
                      : (realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct !== null && realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct !== undefined
                        ? `${realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct > 0 ? '+' : ''}${realWorldVRPResult.benchmark_comparison.qpso_gap_vs_reference_pct}%`
                        : 'N/A')}
                  </span>
                </div>
                <div className="bg-white border border-slate-200 p-1 rounded">
                  <span className="text-[9px] text-slate-400 block uppercase">Time Gap</span>
                  <span className="font-bold text-slate-800 font-mono">
                    {realWorldVRPResult.benchmark_comparison.qpso_time_gap_pct !== null && realWorldVRPResult.benchmark_comparison.qpso_time_gap_pct !== undefined
                      ? `${realWorldVRPResult.benchmark_comparison.qpso_time_gap_pct > 0 ? '+' : ''}${realWorldVRPResult.benchmark_comparison.qpso_time_gap_pct}%`
                      : 'N/A'}
                  </span>
                </div>
                <div className="bg-white border border-slate-200 p-1 rounded">
                  <span className="text-[9px] text-slate-400 block uppercase">Dist Gap</span>
                  <span className="font-bold text-emerald-700 font-mono">
                    {realWorldVRPResult.benchmark_comparison.qpso_dist_gap_pct !== null && realWorldVRPResult.benchmark_comparison.qpso_dist_gap_pct !== undefined
                      ? `${realWorldVRPResult.benchmark_comparison.qpso_dist_gap_pct > 0 ? '+' : ''}${realWorldVRPResult.benchmark_comparison.qpso_dist_gap_pct}%`
                      : '0.00%'}
                  </span>
                </div>
              </div>

              {/* Raw Unrounded Savings vs Greedy */}
              {realWorldVRPResult.benchmark_comparison.raw_savings_vs_greedy && (
                <div className="bg-slate-50 border border-slate-200 rounded p-2 text-[10px] flex justify-between items-center text-slate-700">
                  <span className="font-bold text-slate-500 uppercase text-[9px]">Vs Greedy:</span>
                  <span className="font-mono text-emerald-700 font-semibold">
                    {realWorldVRPResult.benchmark_comparison.raw_savings_vs_greedy.time_saved_min > 0
                      ? `Saves ${realWorldVRPResult.benchmark_comparison.raw_savings_vs_greedy.time_saved_min}m time & ${realWorldVRPResult.benchmark_comparison.raw_savings_vs_greedy.distance_saved_km}km dist`
                      : 'Greedy heuristic baseline'}
                  </span>
                </div>
              )}

              {/* Transparent Scientific Findings Note */}
              <p className="text-[10px] text-slate-500 leading-snug bg-white/70 p-2 rounded border border-slate-200/60">
                <b>Benchmark Insight:</b> Objective J is a dimensionless composite score (not minutes), combining 70% normalized travel time + 30% normalized distance. Classical Reference Solver (OR-Tools Guided Local Search) is evaluated under a 2-second search budget to provide the quality reference. QPSO achieves a feasible schedule under its swarm iteration budget.
              </p>
            </div>

            {/* Individual Vehicle Tours */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Assigned Vehicle Tours ({realWorldVRPResult.results.qpso.routes.length})
              </span>

              <div className="space-y-2">
                {realWorldVRPResult.results.qpso.routes.map((route, idx) => (
                  <div
                    key={route.vehicle_id}
                    className="bg-white border border-slate-200 rounded-xl p-2.5 space-y-1.5 text-xs shadow-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 flex items-center gap-1.5">
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{
                            backgroundColor: ['#059669', '#2563eb', '#7c3aed', '#d97706'][idx % 4]
                          }}
                        />
                        Vehicle {route.vehicle_id + 1}
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        {route.total_travel_time_min} min · {route.total_distance_km} km
                      </span>
                    </div>

                    <div className="text-[10px] text-slate-600 bg-slate-50 p-1.5 rounded-lg border border-slate-100 space-y-0.5">
                      <span className="font-semibold text-slate-700 block">Stops Sequence:</span>
                      <div className="font-medium text-slate-800">
                        {route.full_path_nodes
                          .map((nid) => nid.replace('_', ' ').replace('junction', 'Jct').replace('beach', 'Beach'))
                          .join(' -> ')}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Provenance Box */}
            {/* Input & Data Provenance Box */}
            <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-[10px] text-slate-600 space-y-1">
              <span className="font-bold text-slate-500 uppercase tracking-wider block text-[9px]">Input & Data Provenance</span>
              <div className="flex justify-between">
                <span className="text-slate-400">Road Matrix:</span>
                <span className="font-medium text-slate-800">{realWorldVRPResult.matrix_provenance?.routing_provider || 'OSRM Table API (Real Road Network)'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Vehicle Capacity:</span>
                <span className="font-medium text-slate-800">{realWorldVRPResult.matrix_provenance?.vehicle_capacity_source || '300 kg (Operator-Configured)'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Customer Stops:</span>
                <span className="font-medium text-slate-800">{realWorldVRPResult.matrix_provenance?.customer_stops_source || `${realWorldVRPResult.matrix_metadata.num_stops - 1} Locations (Demo Order Points)`}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Classical Reference:</span>
                <span className="font-medium text-slate-800">{realWorldVRPResult.matrix_provenance?.reference_solver || 'Google OR-Tools (Guided Local Search)'}</span>
              </div>
              {realWorldVRPResult.matrix_provenance?.matrix_generated_at && (
                <div className="flex justify-between border-t border-slate-200/60 pt-1 text-[9px] text-slate-500">
                  <span>Generated:</span>
                  <span className="font-mono text-slate-700">{new Date(realWorldVRPResult.matrix_provenance.matrix_generated_at).toLocaleTimeString()} ({realWorldVRPResult.matrix_provenance.traffic_snapshot_id})</span>
                </div>
              )}
            </div>
          </div>
        ) : vrpResults && vrpResults.qpso ? (
          /* LAB GRAPH TELEMETRY */
          <div className="space-y-3">
            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 space-y-1">
              <div className="flex items-baseline justify-between">
                <div>
                  <span className="text-[10px] font-semibold text-slate-500 uppercase">Total Fleet Travel Time</span>
                  <div className="text-3xl font-black text-slate-900 tracking-tight">
                    {vrpResults.qpso.total_fleet_time_min} <span className="text-sm font-normal text-slate-500">min</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 font-semibold uppercase">Cost</span>
                  <div className="text-base font-bold text-emerald-700 font-mono">
                    {vrpResults.qpso.total_fleet_cost}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200/60 text-[11px]">
                <div>
                  <span className="text-slate-400 text-[9px] block uppercase">Total Distance</span>
                  <span className="text-slate-800 font-bold">{vrpResults.qpso.total_fleet_distance_km} km</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[9px] block uppercase">Compute Time</span>
                  <span className="text-slate-600">{vrpResults.qpso.runtime_ms} ms</span>
                </div>
              </div>
            </div>

            {/* Individual Vehicle Tours */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Assigned Vehicle Tours ({vrpResults.qpso.routes.length})
              </span>

              <div className="space-y-2">
                {vrpResults.qpso.routes.map((route: VehicleRouteData, idx: number) => (
                  <div
                    key={route.vehicle_id}
                    className="bg-white border border-slate-200 rounded-xl p-2.5 space-y-1 text-xs shadow-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 flex items-center gap-1.5">
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{
                            backgroundColor: ['#059669', '#2563eb', '#7c3aed', '#d97706'][idx % 4]
                          }}
                        />
                        Vehicle {route.vehicle_id}
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        {route.total_travel_time_min} min · {route.total_load_kg} kg
                      </span>
                    </div>

                    <div className="text-[10px] font-mono text-slate-600 bg-slate-50 p-1.5 rounded border border-slate-100">
                      Path: {route.full_path_nodes.join(' -> ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-slate-50 border border-dashed border-slate-200 rounded-xl p-4 text-center text-xs text-slate-500">
            Click <b className="text-slate-800">Dispatch Fleet</b> to benchmark multi-vehicle Capacitated VRP on the road network matrix.
          </div>
        )}
      </div>
    </div>
  );
};
