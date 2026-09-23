import React, { useState, useEffect } from 'react';
import { Atom, Play, Terminal, CheckCircle2, ChevronDown, ChevronRight, Cpu } from 'lucide-react';
import { runQAOA } from '../services/api';
import type { QAOAExecutionResponse } from '../types';

export const QuantumInspector: React.FC = () => {
  const [qaoaResult, setQaoaResult] = useState<QAOAExecutionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [pLayers, setPLayers] = useState(2);
  const [showQasm, setShowQasm] = useState(false);

  const executeQuantum = async () => {
    setLoading(true);
    try {
      const res = await runQAOA({ p_layers: pLayers });
      setQaoaResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    executeQuantum();
  }, [pLayers]);

  return (
    <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-6 text-slate-800 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
            <Atom className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-base text-slate-900">
              Quantum Optimization Lab
            </h2>
            <p className="text-xs text-slate-500">
              Small-Scale Ising QUBO Formulation & NumPy Statevector QAOA Simulation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-medium">Ansatz Layers (p):</span>
            <select
              value={pLayers}
              onChange={(e) => setPLayers(parseInt(e.target.value))}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 text-xs font-mono focus:outline-none focus:border-blue-500"
            >
              <option value={1}>p = 1</option>
              <option value={2}>p = 2 (Recommended)</option>
              <option value={3}>p = 3</option>
            </select>
          </div>

          <button
            onClick={executeQuantum}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-sm transition flex items-center gap-1.5 disabled:opacity-50"
          >
            {loading ? (
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-white" />
            )}
            <span>RUN QAOA EXPERIMENT</span>
          </button>
        </div>
      </div>

      {/* Prominent Research Simulation Banner */}
      <div className="bg-amber-50 border border-amber-200/90 rounded-xl p-3 flex items-start gap-3 text-amber-900">
        <Cpu className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-bold text-xs tracking-wide uppercase text-amber-800">
            RESEARCH SIMULATION — NOT USED FOR LIVE ROUTE SELECTION
          </span>
          <p className="text-[11px] text-amber-700 leading-snug">
            QAOA is demonstrated as an exploratory quantum algorithm research component using a classical NumPy statevector simulator. Production routing and commercial fleet dispatch execute on real OpenStreetMap road graphs via classical local search (Google OR-Tools) and quantum-inspired swarm optimization (Random-Key QPSO).
          </p>
        </div>
      </div>

      {/* 4-Step Quantum Formulation Pipeline */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center text-xs">
        <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-2.5 space-y-0.5 shadow-2xs">
          <span className="text-[9px] font-bold text-slate-400 uppercase">Step 1</span>
          <span className="font-bold text-slate-800 block text-[11px]">QUBO Formulation</span>
          <span className="text-[9px] font-mono text-slate-500">min xᵀ Q x</span>
        </div>
        <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-2.5 space-y-0.5 shadow-2xs">
          <span className="text-[9px] font-bold text-slate-400 uppercase">Step 2</span>
          <span className="font-bold text-slate-800 block text-[11px]">Ising Model</span>
          <span className="text-[9px] font-mono text-slate-500">H = ∑ Jᵢⱼ Zᵢ Zⱼ</span>
        </div>
        <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-2.5 space-y-0.5 shadow-2xs">
          <span className="text-[9px] font-bold text-slate-400 uppercase">Step 3</span>
          <span className="font-bold text-slate-800 block text-[11px]">QAOA Circuit</span>
          <span className="text-[9px] font-mono text-slate-500">e⁻ⁱᵞᴴᶜ · e⁻ⁱᵝᴴᵇ</span>
        </div>
        <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-2.5 space-y-0.5 shadow-2xs">
          <span className="text-[9px] font-bold text-slate-400 uppercase">Step 4</span>
          <span className="font-bold text-slate-800 block text-[11px]">Statevector</span>
          <span className="text-[9px] font-mono text-slate-500">|ψ(γ,β)⟩ Probabilities</span>
        </div>
      </div>

      {qaoaResult && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 text-xs">
          {/* Left: Summary & Statevector Distribution (6 cols) */}
          <div className="col-span-12 lg:col-span-6 space-y-4">
            {/* Experiment Overview Cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-[10px] text-slate-500 block uppercase font-medium">Problem</span>
                <span className="font-bold text-slate-900 text-sm">4-Qubit QUBO</span>
              </div>
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-[10px] text-slate-500 block uppercase font-medium">Ansatz Depth</span>
                <span className="font-bold text-blue-600 font-mono text-sm">{qaoaResult.circuit_depth} Gates</span>
              </div>
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-[10px] text-slate-500 block uppercase font-medium">Simulation Time</span>
                <span className="font-bold text-emerald-700 font-mono text-sm">{qaoaResult.runtime_ms} ms</span>
              </div>
            </div>

            {/* Optimal Ground State Box */}
            <div className="bg-emerald-50/60 border border-emerald-200 p-4 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-emerald-900 text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Best Measured QAOA State
                </span>
                <span className="font-mono text-sm text-emerald-800 font-bold bg-white px-2 py-0.5 rounded border border-emerald-200">
                  |{qaoaResult.optimal_bitstring}⟩
                </span>
              </div>
              <p className="text-slate-700 text-xs">
                Corridor Assignment: <span className="font-bold text-slate-900">{qaoaResult.optimal_state_label}</span>
              </p>
              <div className="text-[11px] text-slate-500 font-mono flex gap-4 pt-1">
                <span>Hamiltonian Energy: <b className="text-slate-800">{qaoaResult.optimal_cost}</b></span>
                <span>Simulator: <b className="text-blue-700">NumPy Statevector</b></span>
              </div>
            </div>

            {/* State Probability Distribution Histogram */}
            <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-3">
              <span className="font-bold text-slate-800 text-xs uppercase tracking-wider block">
                Quantum Statevector Probabilities
              </span>
              <div className="space-y-2 font-mono text-xs">
                {Object.entries(qaoaResult.state_probabilities).map(([state, prob]) => {
                  const probNum = typeof prob === 'number' ? prob : parseFloat(prob as string);
                  const isOptimal = state === qaoaResult.optimal_bitstring;
                  return (
                    <div key={state} className="space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span className={isOptimal ? 'text-emerald-700 font-bold' : ''}>
                          |{state}⟩ {isOptimal ? '(Best)' : ''}
                        </span>
                        <span className="font-semibold">{(probNum * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            isOptimal ? 'bg-emerald-600' : 'bg-blue-500'
                          }`}
                          style={{ width: `${probNum * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right: Quantum Circuit & OpenQASM (6 cols) */}
          <div className="col-span-12 lg:col-span-6 space-y-4">
            {/* Visual Circuit */}
            <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-2">
              <span className="font-bold text-slate-800 text-xs uppercase tracking-wider block flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-blue-600" /> Synthesized QAOA Quantum Circuit Wire
              </span>
              <div className="p-3 bg-white rounded-lg border border-slate-200 font-mono text-xs text-blue-900 space-y-1 overflow-x-auto whitespace-pre shadow-inner">
{`q[0]: ──H──RZ(γ)──●───────RX(β)──
q[1]: ──H──RZ(γ)──┼──●────RX(β)──
q[2]: ──H──RZ(γ)──X──┼────RX(β)──
q[3]: ──H──RZ(γ)─────X────RX(β)──`}
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Applies Hadamard initialization H^⊗n, problem Hamiltonian unitary U(C, γ), and transverse mixing unitary U(B, β) across p = {pLayers} layers.
              </p>
            </div>

            {/* Collapsible OpenQASM 2.0 */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
              <button
                onClick={() => setShowQasm(!showQasm)}
                className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
              >
                <span className="flex items-center gap-1.5">
                  <Terminal className="w-4 h-4 text-blue-600" />
                  <span>View OpenQASM 2.0 Circuit Representation</span>
                </span>
                {showQasm ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </button>

              {showQasm && (
                <div className="p-3 border-t border-slate-100 bg-slate-900 text-cyan-300 font-mono text-xs max-h-56 overflow-y-auto whitespace-pre leading-relaxed">
                  {qaoaResult.quantum_circuit_qasm}
                </div>
              )}
            </div>

            {/* Scientific Clarification */}
            <div className="p-4 bg-blue-50/50 border border-blue-100 rounded-xl space-y-1 text-xs text-slate-700">
              <span className="font-bold text-blue-900 block uppercase text-[10px]">
                Quantum vs Quantum-Inspired Distinction
              </span>
              <p className="text-slate-600 leading-relaxed text-[11px]">
                • <b>QPSO</b> is a quantum-inspired classical metaheuristic executed on CPUs for general city-scale routing.<br/>
                • <b>QAOA</b> is a gate-based quantum algorithm designed for NISQ hardware, evaluated here on small reduced QUBO corridors via statevector simulation.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
