import React, { useState, useEffect, useRef } from 'react';
import { MapView } from '../MapView';
import {
  Navigation,
  AlertTriangle,
  Play,
  RotateCcw,
  CheckCircle2,
  Sparkles,
  ArrowUpDown,
  Compass,
  Search,
  MapPin,
  X,
  SlidersHorizontal
} from 'lucide-react';
import { searchPlaces } from '../../services/api';
import type {
  NetworkGeoJSON,
  OptimizeRouteResponse,
  ScenarioPreset,
  Landmark,
  RealWorldRouteResponse,
  SystemStatus,
  PlaceSearchResult
} from '../../types';

interface OperationsViewProps {
  network: NetworkGeoJSON | null;
  originNode: string;
  destinationNode: string;
  setOriginNode: (id: string) => void;
  setDestinationNode: (id: string) => void;
  selectedAlgos: string[];
  setSelectedAlgos: (algos: string[]) => void;
  weights: Record<string, number>;
  setWeights: React.Dispatch<React.SetStateAction<Record<string, number>>>;
  scenarios: ScenarioPreset[];
  onLoadScenario: (scenario: ScenarioPreset) => void;
  onRunOptimization: () => void;
  onResetTraffic: () => void;
  isLoading: boolean;
  selectedEdge: { u: string; v: string } | null;
  onTriggerEdgeIncident: (type: string, multiplier: number, isClosed: boolean) => void;
  routeResults: OptimizeRouteResponse | null;
  onSelectNode: (nodeId: string) => void;
  onSelectEdge: (u: string, v: string) => void;
  landmarks?: Landmark[];
  originLandmark?: string;
  destinationLandmark?: string;
  setOriginLandmark?: (id: string) => void;
  setDestinationLandmark?: (id: string) => void;
  realWorldRoute?: RealWorldRouteResponse | null;
  onRunRealWorldRoute?: (orig?: string, dest?: string, coords?: any) => void;
  routingMode?: 'realworld' | 'research';
  setRoutingMode?: (mode: 'realworld' | 'research') => void;
  systemStatus?: SystemStatus | null;
}

export const OperationsView: React.FC<OperationsViewProps> = ({
  network,
  originNode,
  destinationNode,
  setOriginNode: _setOriginNode,
  setDestinationNode: _setDestinationNode,
  selectedAlgos: _selectedAlgos,
  setSelectedAlgos: _setSelectedAlgos,
  weights: _weights,
  setWeights: _setWeights,
  scenarios: _scenarios,
  onLoadScenario: _onLoadScenario,
  onRunOptimization: _onRunOptimization,
  onResetTraffic,
  isLoading,
  selectedEdge: _selectedEdge,
  onTriggerEdgeIncident: _onTriggerEdgeIncident,
  routeResults,
  onSelectNode,
  onSelectEdge,
  landmarks = [],
  originLandmark = 'rk_beach',
  destinationLandmark = 'rushikonda_beach',
  setOriginLandmark,
  setDestinationLandmark,
  realWorldRoute,
  onRunRealWorldRoute,
  routingMode: _routingMode = 'realworld',
  setRoutingMode: _setRoutingMode,
  systemStatus: _systemStatus
}) => {
  // Dynamic TomTom Place Search State
  const [originSearchQuery, setOriginSearchQuery] = useState('');
  const [destSearchQuery, setDestSearchQuery] = useState('');
  const [originResults, setOriginResults] = useState<PlaceSearchResult[]>([]);
  const [destResults, setDestResults] = useState<PlaceSearchResult[]>([]);
  const [isSearchingOrigin, setIsSearchingOrigin] = useState(false);
  const [isSearchingDest, setIsSearchingDest] = useState(false);
  const [showOriginDropdown, setShowOriginDropdown] = useState(false);
  const [showDestDropdown, setShowDestDropdown] = useState(false);
  const [usePresets, setUsePresets] = useState(false);

  const [selectedOriginPlace, setSelectedOriginPlace] = useState<PlaceSearchResult | null>(null);
  const [selectedDestPlace, setSelectedDestPlace] = useState<PlaceSearchResult | null>(null);
  const [selectedAltIdx, setSelectedAltIdx] = useState<number | null>(null);

  const originInputRef = useRef<HTMLInputElement>(null);
  const destInputRef = useRef<HTMLInputElement>(null);

  // Debounced search for Origin
  useEffect(() => {
    const q = originSearchQuery.trim();
    if (!q || q.length < 2 || usePresets) {
      setOriginResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearchingOrigin(true);
      try {
        const res = await searchPlaces(q, 8);
        setOriginResults(res);
      } catch (e) {
        console.error('Origin search error:', e);
      } finally {
        setIsSearchingOrigin(false);
      }
    }, 280);
    return () => clearTimeout(timer);
  }, [originSearchQuery, usePresets]);

  // Debounced search for Destination
  useEffect(() => {
    const q = destSearchQuery.trim();
    if (!q || q.length < 2 || usePresets) {
      setDestResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearchingDest(true);
      try {
        const res = await searchPlaces(q, 8);
        setDestResults(res);
      } catch (e) {
        console.error('Dest search error:', e);
      } finally {
        setIsSearchingDest(false);
      }
    }, 280);
    return () => clearTimeout(timer);
  }, [destSearchQuery, usePresets]);

  const handleSelectOrigin = (place: PlaceSearchResult) => {
    setSelectedOriginPlace(place);
    setOriginSearchQuery(place.name);
    setShowOriginDropdown(false);
    if (setOriginLandmark) setOriginLandmark(place.id);
  };

  const handleSelectDest = (place: PlaceSearchResult) => {
    setSelectedDestPlace(place);
    setDestSearchQuery(place.name);
    setShowDestDropdown(false);
    if (setDestinationLandmark) setDestinationLandmark(place.id);
  };

  const handleSwapLandmarks = () => {
    const tempOriginP = selectedOriginPlace;
    const tempDestP = selectedDestPlace;
    setSelectedOriginPlace(tempDestP);
    setSelectedDestPlace(tempOriginP);

    const tempOrigQ = originSearchQuery;
    setOriginSearchQuery(destSearchQuery);
    setDestSearchQuery(tempOrigQ);

    if (originLandmark && destinationLandmark && setOriginLandmark && setDestinationLandmark) {
      const tempId = originLandmark;
      setOriginLandmark(destinationLandmark);
      setDestinationLandmark(tempId);
    }
  };

  const handleCalculateRoute = () => {
    setSelectedAltIdx(null);
    if (selectedOriginPlace && selectedDestPlace && onRunRealWorldRoute) {
      onRunRealWorldRoute(originLandmark, destinationLandmark, {
        originLat: selectedOriginPlace.latitude,
        originLon: selectedOriginPlace.longitude,
        destLat: selectedDestPlace.latitude,
        destLon: selectedDestPlace.longitude,
        originName: selectedOriginPlace.name,
        destName: selectedDestPlace.name,
        originPlace: selectedOriginPlace,
        destPlace: selectedDestPlace
      });
    } else if (usePresets && originLandmark && destinationLandmark && onRunRealWorldRoute) {
      onRunRealWorldRoute(originLandmark, destinationLandmark);
    }
  };

  const isDistantLocation =
    destinationLandmark === 'kailasagiri_hill' ||
    (selectedDestPlace?.name?.toLowerCase().includes('kailasagiri') ?? false);

  const trafficSource = realWorldRoute?.primary_route?.traffic_source || '';
  const isTrafficLive =
    trafficSource.includes('TOMTOM') ||
    realWorldRoute?.primary_route?.traffic_freshness === 'LIVE' ||
    realWorldRoute?.traffic?.state === 'LIVE' ||
    realWorldRoute?.traffic?.state === 'PARTIAL';
  const trafficCoverage = realWorldRoute?.traffic?.coverage_pct ?? 0;

  const displayedRealWorldRoute = React.useMemo(() => {
    if (!realWorldRoute) return null;
    if (selectedAltIdx === null || !realWorldRoute.alternative_routes?.[selectedAltIdx]) {
      return realWorldRoute;
    }
    const alt = realWorldRoute.alternative_routes[selectedAltIdx];
    return {
      ...realWorldRoute,
      primary_route: {
        ...realWorldRoute.primary_route,
        distance_m: alt.distance_m,
        distance_km: alt.distance_km,
        duration_s: alt.duration_s,
        duration_min: alt.traffic_duration_min ?? alt.duration_min,
        traffic_duration_min: alt.traffic_duration_min,
        traffic_delay_min: alt.traffic_delay_min,
        geometry_geojson: alt.geometry_geojson,
        speed_sanity: alt.speed_sanity
      }
    };
  }, [realWorldRoute, selectedAltIdx]);

  return (
    <div className="relative w-full h-full overflow-hidden bg-slate-50 select-none">
      {/* ------------------------------------------------------------- */}
      {/* 1. MAP-FIRST CANVAS (Visual Centerpiece)                      */}
      {/* ------------------------------------------------------------- */}
      <div className="absolute inset-0 z-0">
        <MapView
          network={network}
          routeResults={routeResults}
          originNode={originNode}
          destinationNode={destinationNode}
          onSelectNode={onSelectNode}
          onSelectEdge={onSelectEdge}
          mode="driver_route"
          realWorldRoute={displayedRealWorldRoute}
        />
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. FLOATING LEFT SEARCH PANEL (Modern Map Search Affordance)  */}
      {/* ------------------------------------------------------------- */}
      <div className="absolute top-4 left-4 z-20 w-[350px] max-w-[calc(100vw-2rem)] bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-2xl shadow-xl p-4 flex flex-col gap-3 text-slate-800">
        {/* Card Header */}
        <div className="flex items-center justify-between pb-1 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
              <Navigation className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-bold text-sm text-slate-900">Driver Navigation</h2>
              <p className="text-[11px] text-slate-500 font-medium">
                Search places, addresses and points of interest
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setUsePresets(!usePresets)}
              title={usePresets ? 'Switch to dynamic place search' : 'Switch to landmark presets'}
              className={`p-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                usePresets ? 'bg-blue-100 text-blue-700' : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onResetTraffic}
              title="Reset to Normal Free-Flow"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Origin & Destination Search Fields */}
        <div className="relative bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80 space-y-2">
          {/* Vertical Connecting Guide Line */}
          <div className="absolute left-[21px] top-[26px] bottom-[26px] w-[2px] bg-slate-300 border-dashed z-0" />

          {/* ORIGIN INPUT */}
          <div className="relative z-10">
            <div className="flex items-center gap-2">
              <div className="w-3.5 h-3.5 rounded-full bg-blue-600 shrink-0 ring-4 ring-blue-100" />
              {usePresets ? (
                <select
                  value={originLandmark}
                  onChange={(e) => {
                    const lm = landmarks.find((l) => l.id === e.target.value);
                    if (lm) {
                      setOriginLandmark?.(lm.id);
                      setSelectedOriginPlace({
                        id: lm.id,
                        name: lm.name,
                        address: `${lm.name}, Visakhapatnam, Andhra Pradesh`,
                        latitude: lm.lat,
                        longitude: lm.lon,
                        provider: 'TomTom',
                        provider_place_id: lm.id
                      });
                      setOriginSearchQuery(lm.name);
                    }
                  }}
                  aria-label="Origin Landmark"
                  className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 truncate shadow-xs cursor-pointer"
                >
                  {landmarks.map((lm) => (
                    <option key={lm.id} value={lm.id}>
                      {lm.name}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="relative w-full">
                  <input
                    ref={originInputRef}
                    type="text"
                    value={originSearchQuery}
                    onChange={(e) => {
                      setOriginSearchQuery(e.target.value);
                      setShowOriginDropdown(true);
                    }}
                    onFocus={() => setShowOriginDropdown(true)}
                    placeholder="Search origin place, address, junction..."
                    aria-label="Origin Location"
                    className="w-full bg-white border border-slate-200 rounded-lg pl-2.5 pr-6 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                  />
                  {isSearchingOrigin ? (
                    <div className="absolute right-2 top-2 w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  ) : originSearchQuery ? (
                    <button
                      type="button"
                      onClick={() => {
                        setOriginSearchQuery('');
                        setShowOriginDropdown(false);
                      }}
                      className="absolute right-1.5 top-1.5 text-slate-400 hover:text-slate-600 p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  ) : (
                    <Search className="absolute right-2 top-2 w-3 h-3 text-slate-400 pointer-events-none" />
                  )}
                </div>
              )}
            </div>

            {/* Origin Autocomplete Dropdown */}
            {!usePresets && showOriginDropdown && originResults.length > 0 && (
              <div className="absolute left-6 right-0 mt-1 max-h-48 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-lg z-50 divide-y divide-slate-100">
                {originResults.map((place) => (
                  <button
                    key={place.id}
                    type="button"
                    onClick={() => handleSelectOrigin(place)}
                    className="w-full text-left px-3 py-2 hover:bg-blue-50 transition flex items-start gap-2 text-xs"
                  >
                    <MapPin className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-slate-900 truncate">{place.name}</div>
                      <div className="text-[10px] text-slate-500 truncate">{place.address}</div>
                    </div>
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
                      TomTom
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* DESTINATION INPUT */}
          <div className="relative z-10">
            <div className="flex items-center gap-2">
              <div className="w-3.5 h-3.5 rounded-full bg-red-500 shrink-0 ring-4 ring-red-100" />
              {usePresets ? (
                <select
                  value={destinationLandmark}
                  onChange={(e) => {
                    const lm = landmarks.find((l) => l.id === e.target.value);
                    if (lm) {
                      setDestinationLandmark?.(lm.id);
                      setSelectedDestPlace({
                        id: lm.id,
                        name: lm.name,
                        address: `${lm.name}, Visakhapatnam, Andhra Pradesh`,
                        latitude: lm.lat,
                        longitude: lm.lon,
                        provider: 'TomTom',
                        provider_place_id: lm.id
                      });
                      setDestSearchQuery(lm.name);
                    }
                  }}
                  aria-label="Destination Landmark"
                  className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 truncate shadow-xs cursor-pointer"
                >
                  {landmarks.map((lm) => (
                    <option key={lm.id} value={lm.id}>
                      {lm.name}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="relative w-full">
                  <input
                    ref={destInputRef}
                    type="text"
                    value={destSearchQuery}
                    onChange={(e) => {
                      setDestSearchQuery(e.target.value);
                      setShowDestDropdown(true);
                    }}
                    onFocus={() => setShowDestDropdown(true)}
                    placeholder="Search destination place, address..."
                    aria-label="Destination Location"
                    className="w-full bg-white border border-slate-200 rounded-lg pl-2.5 pr-6 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 shadow-xs"
                  />
                  {isSearchingDest ? (
                    <div className="absolute right-2 top-2 w-3 h-3 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                  ) : destSearchQuery ? (
                    <button
                      type="button"
                      onClick={() => {
                        setDestSearchQuery('');
                        setShowDestDropdown(false);
                      }}
                      className="absolute right-1.5 top-1.5 text-slate-400 hover:text-slate-600 p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  ) : (
                    <Search className="absolute right-2 top-2 w-3 h-3 text-slate-400 pointer-events-none" />
                  )}
                </div>
              )}
            </div>

            {/* Destination Autocomplete Dropdown */}
            {!usePresets && showDestDropdown && destResults.length > 0 && (
              <div className="absolute left-6 right-0 mt-1 max-h-48 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-lg z-50 divide-y divide-slate-100">
                {destResults.map((place) => (
                  <button
                    key={place.id}
                    type="button"
                    onClick={() => handleSelectDest(place)}
                    className="w-full text-left px-3 py-2 hover:bg-red-50 transition flex items-start gap-2 text-xs"
                  >
                    <MapPin className="w-3.5 h-3.5 text-red-600 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-slate-900 truncate">{place.name}</div>
                      <div className="text-[10px] text-slate-500 truncate">{place.address}</div>
                    </div>
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
                      TomTom
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Quick Swap Action */}
          <button
            onClick={handleSwapLandmarks}
            title="Swap Origin & Destination"
            aria-label="Swap Origin and Destination"
            className="absolute right-1 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-white border border-slate-200 hover:bg-slate-100 text-slate-500 shadow-xs z-20 transition"
          >
            <ArrowUpDown className="w-3 h-3" />
          </button>
        </div>

        {/* Location Quality Warning (Pre-route landmark check & dynamic road access verification) */}
        {(isDistantLocation || realWorldRoute?.location_advisory) && (
          <div className="bg-amber-50 border border-amber-300 rounded-xl p-2.5 text-xs text-amber-900 space-y-1.5 shadow-2xs">
            <div className="flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block text-[11px]">Location needs confirmation</span>
                <p className="text-[10px] text-amber-800 leading-snug">
                  {realWorldRoute?.location_advisory ||
                    'Destination is 1.57 km from nearest drivable public road (Beach Road).'}
                </p>
              </div>
            </div>
            <div className="flex justify-end pt-1 border-t border-amber-200/50">
              <button
                type="button"
                onClick={() =>
                  alert(
                    'Location Audit: Kailasagiri Hill (17.7540, 83.3724)\n\n' +
                    'Vehicle routes to Beach Road entry gate. Pedestrian access/funicular ropeway available for hilltop park.'
                  )
                }
                className="text-[10px] font-bold text-amber-800 hover:text-amber-950 px-2 py-0.5 bg-amber-100/80 hover:bg-amber-200 rounded-lg transition"
              >
                [ REVIEW LOCATION ]
              </button>
            </div>
            {realWorldRoute?.destination_resolution && (
              <div className="text-[10px] text-amber-900 font-medium pt-1 border-t border-amber-200">
                Routed to: <span className="font-bold">{realWorldRoute.destination_resolution.access_road_name}</span> ({realWorldRoute.destination_resolution.snap_distance_m}m snap)
              </div>
            )}
          </div>
        )}

        {/* System Data Provenance Strip */}
        <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2.5 space-y-1 text-[10px]">
          <div className="flex items-center justify-between text-slate-700 font-medium">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              <span className="font-bold text-slate-400 uppercase text-[9px]">ROUTING</span>
              OSRM · Road Routing
            </span>
            <span className="flex items-center gap-1.5">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isTrafficLive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                }`}
              />
              <span className="font-bold text-slate-400 uppercase text-[9px]">TRAFFIC</span>
              {realWorldRoute?.traffic && (realWorldRoute.traffic.state === 'LIVE' || realWorldRoute.traffic.state === 'PARTIAL')
                ? `TOMTOM · ${realWorldRoute.traffic.state} (${trafficCoverage.toFixed(1)}% cov)`
                : isTrafficLive
                ? 'TOMTOM · LIVE'
                : 'UNAVAILABLE'}
            </span>
          </div>
        </div>

        {/* Primary Call-to-Action Button */}
        <button
          onClick={handleCalculateRoute}
          disabled={isLoading || (!selectedOriginPlace && !usePresets && !originLandmark) || (!selectedDestPlace && !usePresets && !destinationLandmark)}
          className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-md transition flex items-center justify-center gap-2 text-xs disabled:opacity-50 cursor-pointer"
        >
          {isLoading ? (
            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-white" />
          )}
          <span>{isLoading ? 'Routing on Real Roads...' : 'Calculate Real-World Road Route'}</span>
        </button>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 3. FLOATING RIGHT TRIP SUMMARY PANEL (Clean Modern Navigation)*/}
      {/* ------------------------------------------------------------- */}
      <div className="absolute top-4 right-4 z-10 w-[340px] max-w-[calc(100vw-2rem)] bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-2xl shadow-xl p-4 flex flex-col gap-3 text-slate-800 max-h-[calc(100vh-120px)] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-1 border-b border-slate-100">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Trip Summary</span>
          {realWorldRoute && realWorldRoute.status === 'SUCCESS' ? (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Route Found
            </span>
          ) : null}
        </div>

        {/* Result Content */}
        {realWorldRoute && realWorldRoute.status === 'SUCCESS' ? (() => {
          const activeRoute = (selectedAltIdx !== null && realWorldRoute.alternative_routes?.[selectedAltIdx])
            ? realWorldRoute.alternative_routes[selectedAltIdx]
            : realWorldRoute.primary_route;
          const activeSpeedSanity = activeRoute?.speed_sanity || realWorldRoute.speed_sanity;

          return (
            <div className="space-y-3">
              {/* Hero Distance & ETA Metric Card */}
              <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 space-y-2">
                <div className="flex items-baseline justify-between">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                      {selectedAltIdx !== null
                        ? `Alt ${String.fromCharCode(66 + selectedAltIdx)} Travel Time`
                        : realWorldRoute.traffic_rerouting?.is_rerouted
                        ? 'Bypass Travel Time'
                        : 'Estimated Travel Time'}
                    </span>
                    <div className="text-3xl font-black text-slate-900 tracking-tight">
                      {activeRoute.duration_min} <span className="text-sm font-normal text-slate-500">min</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">Distance</span>
                    <div className="text-xl font-bold text-slate-800">
                      {activeRoute.distance_km} <span className="text-xs font-normal text-slate-500">km</span>
                    </div>
                  </div>
                </div>

                {/* Traffic Impact & Speed Indicators */}
                <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
                  <div>
                    {(activeRoute.traffic_delay_min ?? 0) > 0 ? (
                      <span className="font-bold text-amber-600 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                        +{activeRoute.traffic_delay_min} min traffic delay
                      </span>
                    ) : (
                      <span className="font-medium text-emerald-600 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        Normal free-flow conditions
                      </span>
                    )}
                  </div>
                  <div className="font-semibold text-slate-600">
                    {Math.round((activeRoute.distance_km / (Math.max(1, activeRoute.duration_min) / 60.0)) * 10) / 10} km/h avg
                  </div>
                </div>

                {/* Speed Sanity Indicator */}
                {activeSpeedSanity && (
                  <div className={`mt-1 px-2 py-1 rounded-lg text-[10px] font-semibold flex items-center justify-between ${
                    activeSpeedSanity.status === 'VALID'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-amber-50 text-amber-900 border border-amber-300'
                  }`}>
                    <span className="flex items-center gap-1">
                      <span>{activeSpeedSanity.status === 'VALID' ? 'OK' : 'ALERT'}</span>
                      <span>Speed Sanity: {activeSpeedSanity.status} ({activeSpeedSanity.avg_speed_kmh} km/h)</span>
                    </span>
                    <span className="text-[9px] opacity-75">{activeSpeedSanity.status === 'VALID' ? 'Realistic urban speed' : 'Outside urban bounds'}</span>
                  </div>
                )}
              </div>

              {/* Road Access & Location Accuracy Tier */}
              {(realWorldRoute.destination_resolution || realWorldRoute.origin_resolution) && (
                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      Road Access Point
                    </span>
                    {realWorldRoute.destination_resolution && (
                      <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        realWorldRoute.destination_resolution.confidence === 'HIGH'
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                          : realWorldRoute.destination_resolution.confidence === 'MEDIUM'
                          ? 'bg-blue-100 text-blue-800 border border-blue-300'
                          : realWorldRoute.destination_resolution.confidence === 'REVIEW'
                          ? 'bg-amber-100 text-amber-900 border border-amber-300'
                          : 'bg-red-100 text-red-900 border border-red-300'
                      }`}>
                        {realWorldRoute.destination_resolution.confidence} ({realWorldRoute.destination_resolution.snap_distance_m}m snap)
                      </span>
                    )}
                  </div>

                  {realWorldRoute.destination_resolution && (
                    <div className="space-y-0.5">
                      <div className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                        <span className="truncate">{realWorldRoute.destination_resolution.access_road_name || 'Nearest public drivable road'}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 pl-5">
                        Access: {realWorldRoute.destination_resolution.resolution_method}
                        {realWorldRoute.destination_resolution.entry_points_available > 0
                          ? ` · ${realWorldRoute.destination_resolution.entry_points_available} candidates evaluated`
                          : ''}
                      </div>
                    </div>
                  )}

                  {realWorldRoute.origin_resolution && (
                    <div className="pt-1.5 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-600">
                      <span className="text-slate-400">Origin Access:</span>
                      <span className="font-medium text-slate-700 truncate max-w-[180px]">
                        {realWorldRoute.origin_resolution.access_road_name} ({realWorldRoute.origin_resolution.confidence})
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Location Advisory Box (if REVIEW or INVALID) */}
              {realWorldRoute.location_advisory && (
                <div className="bg-amber-50 border border-amber-300 rounded-xl p-2.5 text-xs text-amber-950 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-[11px] text-amber-900">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>Location requires road-access confirmation</span>
                  </div>
                  <p className="text-[10px] leading-snug text-amber-900">
                    {realWorldRoute.location_advisory}
                  </p>
                </div>
              )}

              {/* Route Candidates / Alternatives (Click-to-Select) */}
              {realWorldRoute.alternative_routes && realWorldRoute.alternative_routes.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Route Alternatives (Click to view)
                  </span>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      type="button"
                      onClick={() => setSelectedAltIdx(null)}
                      className={`p-2 rounded-xl text-left transition cursor-pointer ${
                        selectedAltIdx === null
                          ? 'bg-blue-50/90 border-2 border-blue-600 shadow-xs'
                          : 'bg-slate-50 border border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      <div className="text-[9px] font-bold text-blue-700 uppercase tracking-wider">Primary (Fastest)</div>
                      <div className="text-sm font-extrabold text-slate-900">{realWorldRoute.primary_route.duration_min} min</div>
                      <div className="text-[10px] text-slate-500">{realWorldRoute.primary_route.distance_km} km</div>
                    </button>
                    {realWorldRoute.alternative_routes.map((alt, aIdx) => (
                      <button
                        key={aIdx}
                        type="button"
                        onClick={() => setSelectedAltIdx(aIdx)}
                        className={`p-2 rounded-xl text-left transition cursor-pointer ${
                          selectedAltIdx === aIdx
                            ? 'bg-blue-50/90 border-2 border-blue-600 shadow-xs'
                            : 'bg-slate-50 border border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Alt {String.fromCharCode(66 + aIdx)}</div>
                        <div className="text-sm font-bold text-slate-700">{alt.duration_min} min</div>
                        <div className="text-[10px] text-slate-400">{alt.distance_km} km</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* "Why This Route?" Explanation */}
              <div className="bg-blue-50/70 border border-blue-200/70 p-3 rounded-xl space-y-1 shadow-2xs">
                <span className="text-[10px] font-bold text-blue-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Why this route?
                </span>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {selectedAltIdx !== null && realWorldRoute.alternative_routes?.[selectedAltIdx]?.why_this_route
                    ? realWorldRoute.alternative_routes[selectedAltIdx].why_this_route
                    : realWorldRoute.why_this_route ||
                      realWorldRoute.traffic_rerouting?.reroute_reason ||
                      'Authoritative OSRM road route calculated over OpenStreetMap highway vectors.'}
                </p>
              </div>

              {/* Turn-by-Turn Guidance Drawer */}
              <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1">
                    <Compass className="w-3.5 h-3.5 text-blue-600" />
                    Turn-by-Turn Route ({realWorldRoute.primary_route.steps.length} turns)
                  </span>
                </div>

                <div className="max-h-44 overflow-y-auto space-y-1.5 pr-1 text-[11px]">
                  {realWorldRoute.primary_route.steps.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-2 p-1.5 rounded-lg bg-slate-50/80 border border-slate-100">
                      <div className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[9px] shrink-0 mt-0.5">
                        {idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-slate-800 font-semibold leading-tight">
                          {step.instruction}
                        </div>
                        {step.road_name && step.road_name !== 'Unnamed road' && (
                          <div className="text-slate-500 text-[10px] mt-0.5">
                            via {step.road_name}
                          </div>
                        )}
                        <div className="text-slate-400 text-[10px] mt-0.5">
                          {step.distance_m >= 1000 ? `${(step.distance_m / 1000).toFixed(1)} km` : `${step.distance_m.toFixed(0)} m`} ({Math.round(step.duration_s)}s)
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Provenance & Technical Audit Footer */}
              <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-[10px] text-slate-600 space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Road Network:</span>
                  <span className="font-semibold text-slate-700">OpenStreetMap Mapped Topology</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Routing Provider:</span>
                  <span className="font-semibold text-slate-700">OSRM Car Driving Profile</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Traffic Source:</span>
                  <span className="font-semibold text-slate-700">
                    {realWorldRoute.traffic && (realWorldRoute.traffic.state === 'LIVE' || realWorldRoute.traffic.state === 'PARTIAL')
                      ? `TomTom Flow (${realWorldRoute.traffic.state} · ${realWorldRoute.traffic.coverage_pct.toFixed(1)}% cov)`
                      : realWorldRoute.primary_route.traffic_source || 'TomTom'}
                  </span>
                </div>
                {realWorldRoute.step_conservation && (
                  <div className="flex justify-between border-t border-slate-200/60 pt-1">
                    <span className="text-slate-400">Step Invariant:</span>
                    <span className="font-mono text-emerald-700 font-semibold">
                      {realWorldRoute.step_conservation.status} (ΔD: {realWorldRoute.step_conservation.dist_diff_m}m, ΔT: {realWorldRoute.step_conservation.dur_diff_s}s)
                    </span>
                  </div>
                )}
                <div className="flex justify-between pt-1 border-t border-slate-200/60">
                  <span className="text-slate-400">Provider API Latency:</span>
                  <span className="font-mono text-slate-600">{realWorldRoute.computation_ms} ms</span>
                </div>
              </div>
            </div>
          );
        })() : (
          /* Clean Empty State */
          <div className="bg-slate-50 border border-dashed border-slate-200 rounded-xl p-6 text-center text-xs text-slate-500 space-y-1.5">
            <Navigation className="w-6 h-6 text-slate-400 mx-auto" />
            <p className="font-semibold text-slate-700">No route selected</p>
            <p className="text-[11px]">Search an origin and destination to calculate a real-world road route.</p>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 4. FLOATING BOTTOM ROUTE BAR (Dominant Map Presentation)      */}
      {/* ------------------------------------------------------------- */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 bg-slate-900/90 text-white backdrop-blur-md px-4 py-2 rounded-full shadow-lg border border-slate-700/60 flex items-center gap-3 text-xs font-semibold">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-blue-400" />
          <span className="text-slate-200">OSRM · Road Routing</span>
        </span>
        <span className="text-slate-600">|</span>
        <span className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              isTrafficLive
                ? 'bg-emerald-400 animate-pulse'
                : 'bg-slate-400'
            }`}
          />
          <span className="text-slate-200">
            TRAFFIC:{' '}
            {realWorldRoute?.traffic && (realWorldRoute.traffic.state === 'LIVE' || realWorldRoute.traffic.state === 'PARTIAL')
              ? `TOMTOM · ${realWorldRoute.traffic.state} (${realWorldRoute.traffic.coverage_pct.toFixed(1)}% coverage)`
              : isTrafficLive
              ? 'TOMTOM · LIVE'
              : 'UNAVAILABLE'}
          </span>
        </span>
      </div>
    </div>
  );
};