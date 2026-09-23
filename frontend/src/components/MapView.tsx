import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import type { NetworkGeoJSON, OptimizeRouteResponse, VRPResponse, RealWorldRouteResponse, RealWorldVRPResponse } from '../types';

interface MapViewProps {
  network: NetworkGeoJSON | null;
  originNode: string;
  destinationNode: string;
  depotNode?: string;
  mode: 'driver_route' | 'fleet_vrp';
  onSelectNode: (nodeId: string) => void;
  onSelectEdge: (u: string, v: string) => void;
  routeResults: OptimizeRouteResponse | null;
  vrpResults?: VRPResponse | null;
  activeAlgos?: string[];
  realWorldRoute?: RealWorldRouteResponse | null;
  realWorldVRPResult?: RealWorldVRPResponse | null;
  routeViewMode?: 'both' | 'previous' | 'reoptimized';
}

const ALGO_COLORS: Record<string, string> = {
  dijkstra: '#3b82f6', // Blue
  astar: '#2563eb',    // Google Maps Royal Blue
  aco: '#7c3aed',      // Violet
  qpso: '#059669'      // Crisp Emerald Green
};

export const MapView: React.FC<MapViewProps> = ({
  network,
  originNode,
  destinationNode,
  depotNode = '4',
  mode,
  onSelectNode,
  onSelectEdge,
  routeResults,
  vrpResults,
  activeAlgos = [],
  realWorldRoute,
  realWorldVRPResult,
  routeViewMode = 'both'
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layersGroupRef = useRef<L.LayerGroup | null>(null);

  // Initialize map centered on Visakhapatnam
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [17.72, 83.31],
        zoom: 12,
        zoomControl: false,
        attributionControl: false
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap'
      }).addTo(map);

      L.control.zoom({ position: 'topright' }).addTo(map);

      const layerGroup = L.layerGroup().addTo(map);
      layersGroupRef.current = layerGroup;
      mapInstanceRef.current = map;
    }
  }, []);

  // Update map features whenever inputs change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layersGroupRef.current;
    if (!map || !layerGroup || !network) return;

    layerGroup.clearLayers();
    const boundsPoints: L.LatLng[] = [];

    const shouldShowPrevious = routeViewMode === 'both' || routeViewMode === 'previous';
    const shouldShowReoptimized = routeViewMode === 'both' || routeViewMode === 'reoptimized';

    // 1. Render Base Road Edges
    network.features
      .filter((f) => f.properties.type === 'edge')
      .forEach((f) => {
        const coords = f.geometry.coordinates;
        const latLngs: L.LatLngExpression[] = coords.map((c: number[]) => [c[1], c[0]]);
        const isClosed = f.properties.is_closed;
        const multiplier = f.properties.incident_multiplier || 1.0;
        const u = f.properties.u || '';
        const v = f.properties.v || '';

        let color = '#94a3b8'; // Crisp gray for base roads
        let weight = 3.5;
        let opacity = 0.55;
        let dashArray = undefined;

        if (isClosed) {
          color = '#ef4444'; // Red dashed for closed roads
          weight = 5;
          opacity = 0.95;
          dashArray = '6, 8';
        } else if (multiplier > 1.5) {
          color = '#f59e0b'; // Amber for high congestion
          weight = 4.5;
          opacity = 0.85;
        }

        const polyline = L.polyline(latLngs, {
          color,
          weight,
          opacity,
          dashArray,
          lineCap: 'round',
          lineJoin: 'round'
        });

        polyline.bindTooltip(
          `<div style="font-family: sans-serif; font-size: 11px; padding: 2px;">
            <b>${f.properties.name}</b><br/>
            Speed: ${f.properties.free_flow_speed_kmh} km/h | Length: ${f.properties.length_km} km<br/>
            ${
              isClosed
                ? '<span style="color: #ef4444; font-weight: bold;">ROAD BLOCKED (Incident)</span>'
                : multiplier > 1.0
                ? `<span style="color: #d97706; font-weight: bold;">Congested (${multiplier}x BPR Delay)</span>`
                : '<span style="color: #059669;">Normal Flow</span>'
            }
          </div>`,
          { sticky: true }
        );

        polyline.on('click', () => {
          if (u && v) onSelectEdge(u, v);
        });

        polyline.addTo(layerGroup);
      });

    // 2. Render Real-World Route (OSM / OSRM High-Resolution Road Geometry)
    if (mode === 'driver_route' && realWorldRoute && realWorldRoute.status === 'SUCCESS') {
      const primary = realWorldRoute.primary_route;
      if (primary?.geometry_geojson?.coordinates) {
        const coords = primary.geometry_geojson.coordinates;
        const latLngs: L.LatLng[] = coords.map((c: [number, number]) => L.latLng(c[1], c[0]));
        latLngs.forEach((p) => boundsPoints.push(p));

        const isRerouted = !!realWorldRoute.traffic_rerouting?.is_rerouted;
        const hasAlternatives = realWorldRoute.alternative_routes && realWorldRoute.alternative_routes.length > 0;

        // 2A. If REROUTED: Render Previous Plan (Congested Coastal Route) in DASHED RED
        if (isRerouted && hasAlternatives && shouldShowPrevious) {
          const alt = realWorldRoute.alternative_routes[0];
          if (alt.geometry_geojson?.coordinates) {
            const altLatLngs: L.LatLng[] = alt.geometry_geojson.coordinates.map((c: [number, number]) => L.latLng(c[1], c[0]));
            altLatLngs.forEach((p) => boundsPoints.push(p));

            // Translucent red congestion corridor glow
            const congestionGlow = L.polyline(altLatLngs, {
              color: '#ef4444',
              weight: 12,
              opacity: 0.22,
              lineCap: 'round',
              lineJoin: 'round'
            });
            congestionGlow.addTo(layerGroup);

            // White backing casing for dashed line
            const altCasing = L.polyline(altLatLngs, {
              color: '#ffffff',
              weight: 6.5,
              opacity: 0.9,
              lineCap: 'round',
              lineJoin: 'round'
            });
            altCasing.addTo(layerGroup);

            // Bold Dashed Red Polyline for Inaction Plan
            const altPolyline = L.polyline(altLatLngs, {
              color: '#dc2626',
              weight: 4.5,
              opacity: 0.9,
              dashArray: '8, 8',
              lineCap: 'round',
              lineJoin: 'round'
            });

            altPolyline.bindTooltip(
              `<div style="font-family: sans-serif; font-size: 11px; padding: 4px;">
                <b style="color: #dc2626;">PREVIOUS PLAN (Congestion Inaction)</b><br/>
                <b>${alt.duration_min} min</b> (${alt.distance_km} km)<br/>
                <span style="color: #ef4444; font-weight: 600;">Trapped on Beach Road (16 km/h)</span>
              </div>`,
              { sticky: true }
            );
            altPolyline.addTo(layerGroup);
          }
        }

        // 2B. Primary Route: Emerald Solid when Rerouted, Royal Blue when Free-Flow
        if ((!isRerouted) || shouldShowReoptimized) {
          const primaryColor = isRerouted ? '#10b981' : '#2563eb';

          // Outer white casing for sharp visual contrast
          const casing = L.polyline(latLngs, {
            color: '#ffffff',
            weight: 9,
            opacity: 0.95,
            lineCap: 'round',
            lineJoin: 'round'
          });
          casing.addTo(layerGroup);

          const polyline = L.polyline(latLngs, {
            color: primaryColor,
            weight: 6,
            opacity: 0.95,
            lineCap: 'round',
            lineJoin: 'round'
          });

          polyline.bindTooltip(
            `<div style="font-family: sans-serif; font-size: 12px; padding: 4px;">
              <b style="color: ${primaryColor};">${isRerouted ? 'REOPTIMIZED ROUTE (Dynamic Avoidance)' : 'OSM / OSRM ROUTE'}</b><br/>
              <b>${primary.duration_min} min</b> (${primary.distance_km} km)<br/>
              <span style="font-size: 10px; color: ${isRerouted ? '#059669' : '#64748b'}; font-weight: 600;">
                ${isRerouted ? 'Inland Bypass via NH16 — Avoids Coastal Queue' : `${primary.steps.length} turns on real roads`}
              </span>
            </div>`,
            { sticky: true }
          );
          polyline.addTo(layerGroup);
        }

        // Origin Pin A & Destination Pin B on real road endpoints
        if (latLngs.length >= 2) {
          const startPt = latLngs[0];
          const endPt = latLngs[latLngs.length - 1];

          const pinA = L.divIcon({
            className: 'custom-pin-a',
            html: `<div style="
              width: 32px;
              height: 32px;
              background-color: #2563eb;
              color: white;
              font-weight: bold;
              font-size: 14px;
              border-radius: 50% 50% 50% 0;
              transform: rotate(-45deg);
              display: flex;
              align-items: center;
              justify-content: center;
              box-shadow: 0 4px 12px rgba(0,0,0,0.3);
              border: 2px solid white;
            "><span style="transform: rotate(45deg);">A</span></div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 32]
          });
          const markerA = L.marker(startPt, { icon: pinA });
          markerA.bindTooltip(`<b>Origin (A): ${realWorldRoute.origin.name || 'Start'}</b>`, { direction: 'top', offset: [0, -30] });
          markerA.addTo(layerGroup);

          const pinB = L.divIcon({
            className: 'custom-pin-b',
            html: `<div style="
              width: 32px;
              height: 32px;
              background-color: #dc2626;
              color: white;
              font-weight: bold;
              font-size: 14px;
              border-radius: 50% 50% 50% 0;
              transform: rotate(-45deg);
              display: flex;
              align-items: center;
              justify-content: center;
              box-shadow: 0 4px 12px rgba(0,0,0,0.3);
              border: 2px solid white;
            "><span style="transform: rotate(45deg);">B</span></div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 32]
          });
          const markerB = L.marker(endPt, { icon: pinB });
          markerB.bindTooltip(`<b>Destination (B): ${realWorldRoute.destination.name || 'End'}</b>`, { direction: 'top', offset: [0, -30] });
          markerB.addTo(layerGroup);
        }
      }
    }
    // 3. Render Algorithmic Routes on Curated Graph (when realWorldRoute not active)
    else if (mode === 'driver_route' && routeResults && routeResults.results) {
      activeAlgos.forEach((algoKey, index) => {
        const algoRes = routeResults.results[algoKey];
        if (algoRes && algoRes.is_feasible && algoRes.path_geojson) {
          const coords = algoRes.path_geojson.geometry.coordinates;
          const latLngs: L.LatLng[] = coords.map((c: number[]) => L.latLng(c[1], c[0]));
          latLngs.forEach((p) => boundsPoints.push(p));

          const color = ALGO_COLORS[algoKey] || '#2563eb';

          // Outer casing for contrast
          const casingPolyline = L.polyline(latLngs, {
            color: '#ffffff',
            weight: 8 + (activeAlgos.length - index),
            opacity: 0.95,
            lineCap: 'round',
            lineJoin: 'round'
          });
          casingPolyline.addTo(layerGroup);

          const routePolyline = L.polyline(latLngs, {
            color,
            weight: 5.5 + (activeAlgos.length - index),
            opacity: 0.95,
            lineCap: 'round',
            lineJoin: 'round'
          });

          routePolyline.bindTooltip(
            `<div style="font-family: sans-serif; font-size: 12px; padding: 4px;">
              <b style="color: ${color};">${algoRes.algorithm_name.toUpperCase()}</b><br/>
              <b>${algoRes.travel_time_min} min</b> (${algoRes.distance_km} km)
            </div>`,
            { sticky: true }
          );

          routePolyline.addTo(layerGroup);
        }
      });
    }

    // 3. Render Fleet VRP Mode Multi-Vehicle Paths
    if (mode === 'fleet_vrp' && vrpResults && vrpResults.qpso_routes_geojson) {
      vrpResults.qpso_routes_geojson.features.forEach((f) => {
        const coords = f.geometry.coordinates;
        const latLngs: L.LatLng[] = coords.map((c: number[]) => L.latLng(c[1], c[0]));
        latLngs.forEach((p) => boundsPoints.push(p));

        const color = f.properties.color || '#059669';
        const vId = f.properties.vehicle_id;

        const casingPolyline = L.polyline(latLngs, {
          color: '#ffffff',
          weight: 8,
          opacity: 0.95,
          lineCap: 'round',
          lineJoin: 'round'
        });
        casingPolyline.addTo(layerGroup);

        const polyline = L.polyline(latLngs, {
          color,
          weight: 5,
          opacity: 0.95,
          lineCap: 'round',
          lineJoin: 'round'
        });

        polyline.bindTooltip(
          `<div style="font-family: sans-serif; font-size: 11px; padding: 2px;">
            <b>Vehicle ${vId} Tour</b><br/>
            Time: ${f.properties.total_time_min} min | Load: ${f.properties.total_load_kg} kg
          </div>`,
          { sticky: true }
        );

        polyline.addTo(layerGroup);
      });
    }

    // 3B. Render Real-World Fleet VRP Stops (if realWorldVRPResult is active)
    if (mode === 'fleet_vrp' && realWorldVRPResult && realWorldVRPResult.stops_metadata) {
      realWorldVRPResult.stops_metadata.forEach((stop, idx) => {
        const stopLatLng = L.latLng(stop.lat, stop.lon);
        boundsPoints.push(stopLatLng);
        const isDepot = idx === 0 || stop.category === 'depot';
        const pinColor = isDepot ? '#f59e0b' : '#059669';
        const label = isDepot ? 'D' : `${idx}`;

        const customIcon = L.divIcon({
          className: 'custom-realworld-vrp-icon',
          html: `<div style="
            width: 28px;
            height: 28px;
            background-color: ${pinColor};
            color: white;
            font-weight: bold;
            font-size: 11px;
            font-family: sans-serif;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            border: 2px solid white;
          ">${label}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });

        const marker = L.marker([stop.lat, stop.lon], { icon: customIcon });
        marker.bindTooltip(
          `<div style="font-family: sans-serif; font-size: 11px;">
            <b>${isDepot ? 'Depot Hub' : `Customer Stop ${idx}`}: ${stop.name}</b><br/>
            ${!isDepot ? `Demand: ${(stop as any).demand_kg || 50} kg` : 'Fleet Dispatch Center'}
          </div>`,
          { direction: 'top', offset: [0, -14] }
        );
        marker.addTo(layerGroup);
      });
    }

    // 4. Render Nodes (No intermediate node clutter in Operations Mode!)
    network.features
      .filter((f) => f.properties.type === 'node')
      .forEach((f) => {
        const [lon, lat] = f.geometry.coordinates;
        const nodeId = f.properties.id || '';
        const nodeName = f.properties.name || nodeId;
        const nodeLatLng = L.latLng(lat, lon);

        if (mode === 'driver_route') {
          // If realWorldRoute is active, endpoints are already rendered with high accuracy
          if (realWorldRoute && realWorldRoute.status === 'SUCCESS') {
            return;
          }
          // Operations mode: ONLY render Origin Pin (A) and Destination Pin (B)
          const isOrigin = nodeId === originNode;
          const isDest = nodeId === destinationNode;

          if (isOrigin || isDest) {
            boundsPoints.push(nodeLatLng);
            const pinColor = isOrigin ? '#2563eb' : '#ef4444';
            const label = isOrigin ? 'A' : 'B';

            const customIcon = L.divIcon({
              className: 'custom-pin-icon',
              html: `<div style="
                width: 32px;
                height: 32px;
                background-color: ${pinColor};
                color: white;
                font-weight: bold;
                font-size: 14px;
                font-family: sans-serif;
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                border: 2px solid white;
              ">
                <span style="transform: rotate(45deg);">${label}</span>
              </div>`,
              iconSize: [32, 32],
              iconAnchor: [16, 32]
            });

            const marker = L.marker([lat, lon], { icon: customIcon });
            marker.bindTooltip(
              `<div style="font-family: sans-serif; font-size: 11px;">
                <b>${isOrigin ? 'Origin (A)' : 'Destination (B)'}</b><br/>
                ${nodeName}
              </div>`,
              { direction: 'top', offset: [0, -30] }
            );
            marker.addTo(layerGroup);
          }
          // Note: Intermediate nodes are intentionally hidden in operations mode for clean Google-Maps aesthetic!
        } else {
          // If realWorldVRPResult is active, its stops are already rendered
          if (realWorldVRPResult && realWorldVRPResult.stops_metadata) {
            return;
          }
          // VRP Mode: Show Depot and Customer stops
          boundsPoints.push(nodeLatLng);
          const isDepot = nodeId === depotNode;
          const pinColor = isDepot ? '#f59e0b' : '#0284c7';
          const label = isDepot ? 'D' : nodeId;

          const customIcon = L.divIcon({
            className: 'custom-vrp-icon',
            html: `<div style="
              width: 26px;
              height: 26px;
              background-color: ${pinColor};
              color: white;
              font-weight: bold;
              font-size: 11px;
              font-family: sans-serif;
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              box-shadow: 0 2px 8px rgba(0,0,0,0.2);
              border: 2px solid white;
            ">${label}</div>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13]
          });

          const marker = L.marker([lat, lon], { icon: customIcon });
          marker.bindTooltip(
            `<b>${isDepot ? 'Depot Hub' : `Stop ${nodeId}`}: ${nodeName}</b>`,
            { direction: 'top', offset: [0, -14] }
          );
          marker.on('click', () => onSelectNode(nodeId));
          marker.addTo(layerGroup);
        }
      });

    // 5. Smart Auto-Fit Bounds (ensures route and endpoints are always centered and visible)
    if (boundsPoints.length >= 2) {
      try {
        const bounds = L.latLngBounds(boundsPoints);
        map.fitBounds(bounds, {
          paddingTopLeft: [60, 360], // Offset for left floating panel
          paddingBottomRight: [60, 360], // Offset for right floating panel
          maxZoom: 14,
          animate: true
        });
      } catch (e) {
        console.debug('fitBounds skipped:', e);
      }
    }
  }, [network, originNode, destinationNode, depotNode, mode, routeResults, vrpResults, activeAlgos, realWorldRoute, realWorldVRPResult, onSelectNode, onSelectEdge]);

  return (
    <div className="relative w-full h-full overflow-hidden bg-slate-100">
      {/* Map Element */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Minimal Route Legend (Google Maps Style) */}
      <div className="absolute bottom-4 left-4 z-[900] bg-white/95 backdrop-blur-md border border-slate-200 px-3.5 py-2 rounded-xl shadow-lg text-xs text-slate-700 flex items-center gap-3 font-medium">
        {realWorldRoute && realWorldRoute.status === 'SUCCESS' ? (
          realWorldRoute.traffic_rerouting?.is_rerouted ? (
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-3.5 h-1.5 rounded-full bg-[#10b981]" />
                <span className="text-emerald-700 font-bold">Reoptimized Bypass ({realWorldRoute.primary_route.duration_min} min)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3.5 h-0 border-t-2 border-dashed border-red-500" />
                <span className="text-red-600 font-semibold">
                  Previous Plan {(() => {
                    const oldDur = realWorldRoute.traffic_rerouting?.old_duration_min ?? realWorldRoute.alternative_routes?.[0]?.duration_min;
                    return oldDur ? `(${oldDur} min trapped)` : '(Congested)';
                  })()}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded bg-red-500/30 border border-red-400" />
                <span className="text-slate-500 text-[11px]">Beach Road Bottleneck</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="w-3.5 h-1.5 rounded-full bg-[#2563eb]" />
              <span className="text-slate-800 font-semibold">Real OSM Route ({realWorldRoute.provider.toUpperCase()})</span>
              <span className="text-[11px] text-slate-500">· {realWorldRoute.primary_route.steps.length} turns</span>
            </div>
          )
        ) : (
          <>
            <div className="flex items-center gap-1.5">
              <div className="w-3.5 h-1.5 rounded-full bg-[#2563eb]" />
              <span className="text-slate-600">Baseline (A*)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3.5 h-1.5 rounded-full bg-[#059669]" />
              <span className="text-emerald-700 font-semibold">Optimized (QPSO)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3.5 h-1.5 rounded-full bg-[#f59e0b]" />
              <span className="text-amber-700">Congested</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3.5 h-1.5 rounded-full bg-[#ef4444] border-dashed" />
              <span className="text-rose-600">Closed</span>
            </div>
          </>
        )}
      </div>

      {/* Subtle Bottom-Right Data Provenance Tag */}
      {realWorldRoute && realWorldRoute.status === 'SUCCESS' ? (
        <div className="absolute bottom-4 right-4 z-[900] bg-white/95 backdrop-blur-sm border border-slate-200/90 px-3 py-1.5 rounded-lg text-[10px] text-slate-700 font-medium shadow-sm flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500"></span>
          Roads: OpenStreetMap • Routing: OSRM Profile • Traffic: {realWorldRoute.primary_route.traffic_source || 'Simulation'}
        </div>
      ) : (
        <div className="absolute bottom-4 right-4 z-[900] bg-white/90 backdrop-blur-sm border border-slate-200/80 px-2.5 py-1 rounded-lg text-[10px] text-slate-500 font-medium shadow-sm">
          Curated Visakhapatnam Network • BPR Dynamics
        </div>
      )}
    </div>
  );
};
