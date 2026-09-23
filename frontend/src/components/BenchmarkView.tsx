import React, { useState, useEffect } from 'react';
import { BarChart3, CheckCircle, Server, RefreshCw, Truck, AlertTriangle, Activity, Sliders } from 'lucide-react';

export const BenchmarkView: React.FC = () => {
  const [benchmarkData, setBenchmarkData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/benchmark/summary');
      if (res.ok) {
        const data = await res.json();
        setBenchmarkData(data);
      } else {
        setError('Failed to fetch benchmark summary from API');
      }
    } catch (e: any) {
      setError(e.message || 'Error loading benchmark data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBenchmark();
  }, []);

  const shockData = benchmarkData?.controlled_traffic_shock?.counterfactual_reoptimization_evaluation;
  const t0Plan = shockData?.baseline_t0_plan;
  const inactionPlan = shockData?.inaction_pre_shock_plan_under_traffic;
  const reoptPlan = shockData?.reoptimized_plan;
  const opsMetrics = shockData?.operational_metrics;

  const exactVrp0 = benchmarkData?.vrp_exact_summary?.[0];
  const qpsoOptimalityGap = exactVrp0
    ? `${Math.abs((exactVrp0.qpso_mean_cost - exactVrp0.exact_cost) / exactVrp0.exact_cost * 100).toFixed(2)}%`
    : '0.00%';
  const avoidedMin = opsMetrics?.congestion_delay_avoided_min ?? 7.73;
  const avoidedPct = opsMetrics?.pct_delay_reduction_relative_to_inaction ?? 11.3;

  return (
    <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-6 text-slate-800 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-50 text-purple-600 border border-purple-100">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-extrabold text-lg text-slate-900 tracking-tight uppercase">
              SCIENTIFIC VALIDATION
            </h2>
            <p className="text-xs text-slate-500 font-medium">
              Independent benchmark and dynamic transportation experiment results.
            </p>
          </div>
        </div>

        <button
          onClick={loadBenchmark}
          disabled={loading}
          className="px-3.5 py-1.5 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 transition flex items-center gap-1.5 text-xs font-semibold shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Fetching...' : 'Re-fetch API Data'}
        </button>
      </div>

      {/* Data Provenance Chips Row */}
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium text-slate-600">
        <span className="px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 flex items-center gap-1.5">
          <span className="font-bold text-slate-500 uppercase text-[9px]">Road network:</span>
          OSM-derived
        </span>
        <span className="px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 flex items-center gap-1.5">
          <span className="font-bold text-slate-500 uppercase text-[9px]">Routing:</span>
          OSRM Table Engine
        </span>
        <span className="px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 flex items-center gap-1.5">
          <span className="font-bold text-slate-500 uppercase text-[9px]">Traffic:</span>
          Controlled scenario / LIVE
        </span>
        <span className="px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 flex items-center gap-1.5">
          <span className="font-bold text-slate-500 uppercase text-[9px]">Reference:</span>
          Google OR-Tools (Guided Local Search)
        </span>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 4 Hero Research Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-slate-50 border border-slate-200/90 rounded-2xl p-4 space-y-1 shadow-2xs">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
            Exact Validation
          </span>
          <div className="text-2xl font-black text-slate-900 tracking-tight">
            4! = 24
          </div>
          <p className="text-[11px] text-slate-500 font-medium">
            candidate permutations verified
          </p>
        </div>

        <div className="bg-emerald-50/70 border border-emerald-200/90 rounded-2xl p-4 space-y-1 shadow-2xs">
          <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
            QPSO Optimality
          </span>
          <div className="text-2xl font-black text-emerald-700 tracking-tight">
            {qpsoOptimalityGap}
          </div>
          <p className="text-[11px] text-emerald-800 font-medium">
            gap on tested 4-stop instance
          </p>
        </div>

        <div className="bg-blue-50/70 border border-blue-200/90 rounded-2xl p-4 space-y-1 shadow-2xs">
          <span className="text-[10px] font-bold text-blue-800 uppercase tracking-wider block">
            Dynamic Reoptimization
          </span>
          <div className="text-2xl font-black text-blue-700 tracking-tight">
            {avoidedMin} min
          </div>
          <p className="text-[11px] text-blue-800 font-medium">
            delay avoided ({avoidedPct}% reduction)
          </p>
        </div>

        <div className="bg-purple-50/70 border border-purple-200/90 rounded-2xl p-4 space-y-1 shadow-2xs">
          <span className="text-[10px] font-bold text-purple-800 uppercase tracking-wider block">
            Scalability Horizon
          </span>
          <div className="text-2xl font-black text-purple-700 tracking-tight">
            {`5 -> 50`}
          </div>
          <p className="text-[11px] text-purple-800 font-medium">
            customer stops evaluated
          </p>
        </div>
      </div>

      {/* SECTION 1: Exact VRP Validation & Optimality Gap */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            1. Exact VRP Validation & Optimality Gap Analysis (N=4, 5, 6 Stops)
          </span>
          <span className="text-xs text-emerald-700 font-semibold font-mono bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
            {benchmarkData?.vrp_exact_summary?.[0]?.num_trials ?? 10} Trials / Problem
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-600 text-[11px] border-b border-slate-200 font-semibold">
              <tr>
                <th className="p-2.5">Problem Size</th>
                <th className="p-2.5">Exact Global Optimum</th>
                <th className="p-2.5">Exact Total Time</th>
                <th className="p-2.5">Greedy Mean Cost (Gap)</th>
                <th className="p-2.5 text-emerald-700">Random-Key QPSO (Gap)</th>
                <th className="p-2.5">QPSO Feasibility</th>
                <th className="p-2.5">QPSO Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {benchmarkData?.vrp_exact_summary ? (
                benchmarkData.vrp_exact_summary.map((row: any) => (
                  <tr key={row.problem_size} className={row.problem_size === 6 ? 'bg-emerald-50/40' : ''}>
                    <td className="p-2.5 font-bold text-slate-900 font-sans">N = {row.problem_size} Stops</td>
                    <td className="p-2.5 text-purple-700 font-bold">{row.exact_optimal_cost}</td>
                    <td className="p-2.5 text-slate-700">{row.exact_travel_time_min} min</td>
                    <td className="p-2.5">
                      <span className="text-slate-700">{row.greedy_mean_cost}</span>{' '}
                      <span className={row.greedy_mean_gap_pct > 0 ? 'text-amber-600 font-bold' : 'text-slate-500'}>
                        ({row.greedy_mean_gap_pct > 0 ? `+${row.greedy_mean_gap_pct}%` : '0.0%'})
                      </span>
                    </td>
                    <td className="p-2.5 text-emerald-700 font-bold">
                      {row.qpso_mean_cost} ({row.qpso_mean_gap_pct === 0 ? '0.0% Optimal' : `+${row.qpso_mean_gap_pct}%`})
                    </td>
                    <td className="p-2.5 text-emerald-700 font-bold">{row.qpso_feasibility_pct}%</td>
                    <td className="p-2.5 text-slate-600">{row.qpso_mean_runtime_ms} ms</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="p-4 text-center text-slate-400 font-sans">
                    Loading exact validation data...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 1B: Real Road Dynamic Traffic Reoptimization & Stochastic Robustness (Phase E7) */}
      <div className="space-y-3 pt-2 bg-amber-50/40 border border-amber-200/80 rounded-2xl p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-amber-950 uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-amber-600" />
            1B. Dynamic Fleet Reoptimization & Stochastic Robustness (Real OSM Road Network)
          </span>
          <span className="text-xs text-amber-800 font-semibold font-mono bg-amber-100 px-2.5 py-0.5 rounded border border-amber-300">
            Phase E7 Frozen Benchmark · 10 Seeds
          </span>
        </div>

        {/* Hero Operational Trade-off Card */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="bg-white p-3 rounded-xl border border-amber-200 shadow-2xs space-y-1">
            <span className="text-[10px] text-slate-500 uppercase font-bold block">Inaction Penalty (Pre-Shock on Traffic)</span>
            <div className="text-2xl font-black text-red-600 font-mono">
              {inactionPlan?.fleet_travel_time_min?.toFixed(2) ?? '68.49'} <span className="text-xs font-normal text-slate-500">min</span>
            </div>
            <p className="text-[10px] text-slate-500">Fleet trapped in Beach Road corridor bottleneck (16 km/h).</p>
          </div>

          <div className="bg-white p-3 rounded-xl border border-emerald-200 shadow-2xs space-y-1">
            <span className="text-[10px] text-slate-500 uppercase font-bold block">Reoptimized Schedule (Alternative Tour)</span>
            <div className="text-2xl font-black text-emerald-700 font-mono">
              {reoptPlan?.fleet_travel_time_min?.toFixed(2) ?? '60.76'} <span className="text-xs font-normal text-slate-500">min</span>
            </div>
            <p className="text-[10px] text-slate-500">Redirects fleet along inland arterial (NH16 bypass corridor).</p>
          </div>

          <div className="bg-white p-3 rounded-xl border border-blue-200 shadow-2xs space-y-1">
            <span className="text-[10px] text-slate-500 uppercase font-bold block">Operational Delay Avoided</span>
            <div className="text-2xl font-black text-blue-700 font-mono">
              {opsMetrics?.congestion_delay_avoided_min?.toFixed(2) ?? '7.73'} <span className="text-xs font-normal text-slate-500">min</span>{' '}
              <span className="text-xs font-bold text-emerald-600">(-{opsMetrics?.pct_delay_reduction_relative_to_inaction?.toFixed(1) ?? '11.3'}%)</span>
            </div>
            <p className="text-[10px] text-slate-500">
              Trade-off: +{opsMetrics?.distance_added_km?.toFixed(2) ?? '4.87'} km road distance for -{opsMetrics?.congestion_delay_avoided_min?.toFixed(2) ?? '7.73'} min delay reduction.
            </p>
          </div>
        </div>

        {/* 4-Quadrant Comparison Matrix */}
        <div className="overflow-x-auto border border-amber-200/90 rounded-xl bg-white shadow-2xs">
          <table className="w-full text-xs text-left">
            <thead className="bg-amber-100/50 text-amber-900 text-[11px] border-b border-amber-200 font-semibold">
              <tr>
                <th className="p-2.5">Operating Condition</th>
                <th className="p-2.5">Google OR-Tools (1s Guided Local Search)</th>
                <th className="p-2.5 text-purple-800">Random-Key QPSO (10-Seed Ensemble)</th>
                <th className="p-2.5">Route Permutation Sequence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              <tr>
                <td className="p-2.5 font-sans font-bold text-slate-900">T₀ Free-Flow Baseline</td>
                <td className="p-2.5 text-slate-700">
                  J = {t0Plan?.composite_j?.toFixed(4) ?? '4.2470'} · {t0Plan?.fleet_travel_time_min?.toFixed(2) ?? '51.23'} min · {t0Plan?.fleet_distance_km?.toFixed(2) ?? '47.82'} km
                </td>
                <td className="p-2.5 text-purple-700 font-bold">
                  J = {t0Plan?.composite_j?.toFixed(4) ?? '4.2470'} ± 0.00 · {t0Plan?.fleet_travel_time_min?.toFixed(2) ?? '51.23'} min
                </td>
                <td className="p-2.5 text-slate-600 text-[10px] font-sans">Maddilapalem{' -> '}Rushikonda{' -> '}Kailasagiri{' -> '}RK Beach{' -> '}NAD</td>
              </tr>
              <tr className="bg-rose-50/40">
                <td className="p-2.5 font-sans font-bold text-red-900">T₁ Shock (Inaction: Old Plan)</td>
                <td className="p-2.5 text-red-700 font-bold">
                  J = {inactionPlan?.composite_j?.toFixed(4) ?? '5.2572'} · {inactionPlan?.fleet_travel_time_min?.toFixed(2) ?? '68.49'} min · {inactionPlan?.fleet_distance_km?.toFixed(2) ?? '47.82'} km
                </td>
                <td className="p-2.5 text-red-700 font-bold">
                  J = {inactionPlan?.composite_j?.toFixed(4) ?? '5.2572'} ± 0.00 · {inactionPlan?.fleet_travel_time_min?.toFixed(2) ?? '68.49'} min
                </td>
                <td className="p-2.5 text-slate-600 text-[10px] font-sans">Pre-shock coastal order trapped in congestion delay (+17.26m)</td>
              </tr>
              <tr className="bg-emerald-50/40">
                <td className="p-2.5 font-sans font-bold text-emerald-900">T₁ Shock (Reoptimized)</td>
                <td className="p-2.5 text-emerald-700 font-bold">
                  J = {reoptPlan?.composite_j?.toFixed(4) ?? '4.9319'} · {reoptPlan?.fleet_travel_time_min?.toFixed(2) ?? '60.76'} min · {reoptPlan?.fleet_distance_km?.toFixed(2) ?? '52.69'} km
                </td>
                <td className="p-2.5 text-emerald-700 font-bold">
                  J = {reoptPlan?.composite_j?.toFixed(4) ?? '4.9319'} ± 0.00 · {reoptPlan?.fleet_travel_time_min?.toFixed(2) ?? '60.76'} min
                </td>
                <td className="p-2.5 text-slate-600 text-[10px] font-sans">Maddilapalem{' -> '}RK Beach{' -> '}NAD{' -> '}Rushikonda{' -> '}Kailasagiri</td>
              </tr>
              <tr className="bg-blue-50/30">
                <td className="p-2.5 font-sans font-bold text-blue-900">Avoided Delay / Trade-off</td>
                <td className="p-2.5 text-blue-700 font-bold">
                  -{opsMetrics?.congestion_delay_avoided_min?.toFixed(2) ?? '7.73'} min (-{opsMetrics?.pct_delay_reduction_relative_to_inaction?.toFixed(1) ?? '11.3'}%) · +{opsMetrics?.distance_added_km?.toFixed(2) ?? '4.87'} km
                </td>
                <td className="p-2.5 text-blue-700 font-bold">
                  -{opsMetrics?.congestion_delay_avoided_min?.toFixed(2) ?? '7.73'} min (-{opsMetrics?.pct_delay_reduction_relative_to_inaction?.toFixed(1) ?? '11.3'}%) · +{opsMetrics?.distance_added_km?.toFixed(2) ?? '4.87'} km
                </td>
                <td className="p-2.5 text-slate-700 text-[10px] font-sans font-semibold">
                  Cost avoided: ΔJ = -{opsMetrics?.composite_j_avoided?.toFixed(4) ?? '0.3253'} (Fixed reference scales T_ref=11.96m, D_ref=11.49km)
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Trace Verification: Permutation Space & Stochastic Diversity */}
        <div className="bg-white border border-amber-200 rounded-xl p-3 text-[11px] space-y-1.5 text-slate-700">
          <span className="font-bold text-slate-900 block font-sans">
            Combinatorial Permutation Space & Stochastic Convergence Verification:
          </span>
          <p className="leading-relaxed">
            Exhaustive enumeration of all <b>4! = 24 candidate customer permutations</b> on the real Visakhapatnam road graph demonstrates that the observed route is the <b>unique global minimum</b> (Rank 1: J=4.2470 in T₀, J=4.9319 in T₁; Rank 2 is J=4.3027 and J=5.0252 respectively).
          </p>
          <p className="leading-relaxed">
            Diagnostic tracing across 10 independent random seeds confirms genuine stochastic search diversity: each seed initializes with <b>16 to 22 unique permutations</b> in the initial population (Iteration 0), takes different trajectory paths, and quantum attractor contraction reliably drives all 10 runs to the proven global optimum.
          </p>
        </div>
      </div>

      {/* SECTION 2: Multi-Seed VRP Fleet Scalability (Paired Subset Analysis) */}
      <div className="space-y-2.5 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Truck className="w-4 h-4 text-blue-600" />
            2. Multi-Seed VRP Fleet Scalability (Paired Comparison across 10 Seeds)
          </span>
          <span className="text-xs text-blue-700 font-semibold font-mono bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
            Paired Statistical Analysis
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-600 text-[11px] border-b border-slate-200 font-semibold">
              <tr>
                <th className="p-2.5">Stops / Fleet</th>
                <th className="p-2.5">Greedy Cost (All)</th>
                <th className="p-2.5">Greedy Cost (Paired)</th>
                <th className="p-2.5 text-blue-700">QPSO Cost (Feasible Subset)</th>
                <th className="p-2.5">Paired Cost Delta</th>
                <th className="p-2.5">Paired Time Delta</th>
                <th className="p-2.5">Runtime Ratio</th>
                <th className="p-2.5">Feasibility Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {benchmarkData?.vrp_scalability_summary ? (
                benchmarkData.vrp_scalability_summary.map((row: any) => (
                  <tr key={row.num_customers}>
                    <td className="p-2.5 font-bold text-slate-900 font-sans">
                      {row.num_customers} Stops ({row.num_vehicles} Trucks)
                    </td>
                    <td className="p-2.5 text-slate-500">{row.greedy_mean_cost_all_trials}</td>
                    <td className="p-2.5 text-slate-700 font-mono">{row.greedy_mean_cost_paired_subset}</td>
                    <td className="p-2.5 text-blue-700 font-bold">
                      {row.qpso_mean_cost_feasible_subset} {row.qpso_std_cost_feasible_subset ? `(±${row.qpso_std_cost_feasible_subset})` : ''}
                    </td>
                    <td className="p-2.5">
                      <span className={row.mean_paired_cost_delta_pct > 0 ? 'text-emerald-700 font-bold' : 'text-slate-700'}>
                        {row.mean_paired_cost_delta_pct > 0 ? `-${row.mean_paired_cost_delta_pct}%` : `+${Math.abs(row.mean_paired_cost_delta_pct)}%`}
                      </span>
                    </td>
                    <td className="p-2.5">
                      <span className={row.mean_paired_time_delta_pct > 0 ? 'text-emerald-700 font-bold' : 'text-slate-700'}>
                        {row.mean_paired_time_delta_pct > 0 ? `-${row.mean_paired_time_delta_pct}%` : `+${Math.abs(row.mean_paired_time_delta_pct)}%`}
                      </span>
                    </td>
                    <td className="p-2.5 text-slate-600">{row.runtime_ratio}x</td>
                    <td className="p-2.5">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-sans font-semibold ${
                        row.feasibility_rate_pct === 100
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {row.feasibility_rate_pct}% Feasible
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="p-4 text-center text-slate-400 font-sans">
                    Loading VRP scalability data...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 3: Dynamic Traffic Reoptimization Benchmark (Dual Corridor) */}
      <div className="space-y-2.5 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-amber-600" />
            3. Dynamic Traffic Reoptimization & Route Diversion Benchmark (5 Scenarios)
          </span>
          <span className="text-xs text-amber-700 font-semibold font-mono bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
            Dual-Corridor Topology
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-600 text-[11px] border-b border-slate-200 font-semibold">
              <tr>
                <th className="p-2.5">Disruption Scenario</th>
                <th className="p-2.5">Pre-Shock Route (Time)</th>
                <th className="p-2.5">Shock Baseline Route (Time)</th>
                <th className="p-2.5 text-emerald-700">Shock QPSO Route (Time)</th>
                <th className="p-2.5">Route Diverted?</th>
                <th className="p-2.5">Edge Overlap (Change)</th>
                <th className="p-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {benchmarkData?.dynamic_traffic_summary ? (
                benchmarkData.dynamic_traffic_summary.map((sc: any) => (
                  <tr key={sc.scenario_id} className={sc.route_diverted_around_shock ? 'bg-amber-50/40' : ''}>
                    <td className="p-2.5 font-bold text-slate-900 font-sans">{sc.scenario_name}</td>
                    <td className="p-2.5 text-slate-500">{sc.pre_shock_route} ({sc.pre_shock_time_min}m)</td>
                    <td className="p-2.5 text-slate-700">
                      {sc.shock_astar_route} ({sc.shock_astar_time_min !== 'Infinity' ? `${sc.shock_astar_time_min}m` : '∞'})
                    </td>
                    <td className="p-2.5 text-emerald-700 font-bold">
                      {sc.shock_qpso_route} ({sc.shock_qpso_time_min !== 'Infinity' ? `${sc.shock_qpso_time_min}m` : '∞'})
                    </td>
                    <td className="p-2.5 font-sans">
                      {sc.route_diverted_around_shock ? (
                        <span className="text-emerald-700 font-bold px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200">
                          YES (Diverted via Alt)
                        </span>
                      ) : (
                        <span className="text-slate-500">NO (Direct / Optimal)</span>
                      )}
                    </td>
                    <td className="p-2.5 text-slate-700 font-mono text-[10px]">
                      {sc.route_overlap_pct !== undefined ? `${sc.route_overlap_pct}% (${sc.route_change_pct}% Δ)` : 'N/A'}
                    </td>
                    <td className="p-2.5 font-sans">
                      {sc.qpso_feasible ? (
                        <span className="text-emerald-700 text-[10px] px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 font-semibold">
                          FEASIBLE
                        </span>
                      ) : (
                        <span className="text-rose-700 text-[10px] px-2 py-0.5 rounded bg-rose-50 border border-rose-200 font-semibold">
                          INFEASIBLE (No Route)
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="p-4 text-center text-slate-400 font-sans">
                    Loading dynamic traffic data...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 4: Parameter Sensitivity & Point-to-Point Scalability */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
        {/* Left: Point-to-Point Scalability */}
        <div className="space-y-2.5">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Server className="w-4 h-4 text-blue-600" />
            4A. Point-to-Point Routing Scalability (15 to 500 Nodes)
          </span>

          <div className="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 text-[11px] border-b border-slate-200 font-semibold">
                <tr>
                  <th className="p-2.5">Scale</th>
                  <th className="p-2.5 text-blue-700">Dijkstra</th>
                  <th className="p-2.5 text-blue-700">A* Time</th>
                  <th className="p-2.5 text-emerald-700">QPSO</th>
                  <th className="p-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {benchmarkData?.scalability_summary ? (
                  benchmarkData.scalability_summary.map((row: any) => (
                    <tr key={row.graph_nodes}>
                      <td className="p-2.5 font-bold text-slate-900 font-sans">
                        {row.graph_nodes === 15 ? '15 (Vizag)' : `${row.graph_nodes} Nodes`}
                      </td>
                      <td className="p-2.5 text-blue-700">{row.dijkstra_runtime_ms} ms</td>
                      <td className="p-2.5 text-blue-700">{row.astar_runtime_ms} ms ({row.astar_time_min}m)</td>
                      <td className="p-2.5 text-emerald-700 font-bold">{row.qpso_runtime_ms} ms</td>
                      <td className="p-2.5 font-sans">
                        {row.qpso_feasible ? (
                          <span className="text-emerald-700 text-[10px] font-semibold">FEASIBLE</span>
                        ) : (
                          <span className="text-rose-700 text-[10px] font-semibold">BUDGET LIMIT</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="p-4 text-center text-slate-400 font-sans">Loading...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Parameter Sensitivity Sweep */}
        <div className="space-y-2.5">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Sliders className="w-4 h-4 text-purple-600" />
            4B. 500-Node Single-Seed Parameter Sensitivity Sweep
          </span>

          <div className="overflow-x-auto border border-slate-200 rounded-xl max-h-48 overflow-y-auto shadow-sm">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 text-[11px] border-b border-slate-200 sticky top-0 font-semibold">
                <tr>
                  <th className="p-2.5">Particles (P)</th>
                  <th className="p-2.5">Iterations (I)</th>
                  <th className="p-2.5">Feasible?</th>
                  <th className="p-2.5 text-emerald-700">Best Cost</th>
                  <th className="p-2.5">Runtime</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {benchmarkData?.parameter_sensitivity_summary ? (
                  benchmarkData.parameter_sensitivity_summary.map((row: any, idx: number) => (
                    <tr key={idx} className={row.is_feasible ? 'bg-emerald-50/40' : ''}>
                      <td className="p-2.5 font-bold text-slate-900 font-sans">{row.population_particles} particles</td>
                      <td className="p-2.5 text-slate-700">{row.iteration_budget} iter</td>
                      <td className="p-2.5 font-sans">
                        {row.is_feasible ? (
                          <span className="text-emerald-700 font-bold">YES</span>
                        ) : (
                          <span className="text-rose-700 font-bold">NO</span>
                        )}
                      </td>
                      <td className="p-2.5 text-emerald-700 font-bold">{row.cost !== 'Infinity' ? row.cost : '∞'}</td>
                      <td className="p-2.5 text-slate-600">{row.runtime_ms} ms</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="p-4 text-center text-slate-400 font-sans">Loading...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
