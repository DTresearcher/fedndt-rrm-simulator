import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  BarChart3,
  BrainCircuit,
  Calculator,
  Gauge,
  GitBranch,
  Network,
  RadioTower,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'
import {
  defaultControls,
  formatStrategy,
  round,
  runSimulation,
  type SimulationControls,
} from './simulation/fedndtSimulation'

type SliderProps = {
  label: string
  value: number
  min: number
  max: number
  step?: number
  suffix?: string
  onChange: (value: number) => void
}

function SliderControl({ label, value, min, max, step = 1, suffix = '', onChange }: SliderProps) {
  return (
    <label className="block rounded-2xl border border-white/10 bg-white/[0.035] p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm text-slate-300">{label}</span>
        <span className="rounded-full bg-cyan-400/10 px-2 py-1 text-xs font-semibold text-cyan-200">
          {value}
          {suffix}
        </span>
      </div>
      <input
        className="w-full accent-cyan-300"
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}

function FormulaCard({ title, formula, note }: { title: string; formula: string; note: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-200">{title}</h3>
      <pre className="mt-3 overflow-x-auto rounded-2xl bg-black/30 p-4 text-sm leading-6 text-slate-100">
        {formula}
      </pre>
      <p className="mt-3 text-sm leading-6 text-slate-400">{note}</p>
    </div>
  )
}

function App() {
  const [controls, setControls] = useState<SimulationControls>(defaultControls)
  const result = useMemo(() => runSimulation(controls), [controls])

  const fedndt = result.summaries.find((summary) => summary.strategy === 'fedndt')
  const chartSummaries = result.summaries.map((summary) => ({
    strategy: formatStrategy(summary.strategy),
    avgLatencyMs: round(summary.avgLatencyMs, 1),
    p95LatencyMs: round(summary.p95LatencyMs, 1),
    p99LatencyMs: round(summary.p99LatencyMs, 1),
    slaViolationRate: round(summary.slaViolationRate * 100, 1),
    throughputFairness: round(summary.throughputFairness, 3),
  }))

  const architecture = [
    {
      title: 'Simulated Edge/RAN Environment',
      value: `${result.architectureValues.nodes} nodes / ${result.architectureValues.users} users`,
      description: 'Synthetic users, demand, mobility, radio noise, and overload conditions.',
      icon: RadioTower,
    },
    {
      title: 'Telemetry Generator',
      value: `avg demand ${result.architectureValues.avgDemand}`,
      description: 'Creates deterministic scenario telemetry from browser-side controls.',
      icon: Activity,
    },
    {
      title: 'Local Network Digital Twin',
      value: `capacity ${result.architectureValues.avgCapacityMbps} Mbps`,
      description: 'Builds node-level state for demand, congestion, radio quality, and prediction.',
      icon: Network,
    },
    {
      title: 'Federated Prediction Layer',
      value: `α ${controls.alpha} / β ${controls.beta}`,
      description: 'Uses lightweight demand prediction inspired by local model updates.',
      icon: GitBranch,
    },
    {
      title: 'Incentive / Reliability Engine',
      value: `R̄ ${result.architectureValues.avgReliability}`,
      description: 'Scores freshness, accuracy, consistency, and participation.',
      icon: ShieldCheck,
    },
    {
      title: 'Resource Allocation Optimizer',
      value: `${result.architectureValues.totalResources} units`,
      description: 'Compares static, greedy, and FedNDT-Incentive resource allocation.',
      icon: BrainCircuit,
    },
    {
      title: 'QoS and Utility Evaluation',
      value: `p95 ${result.architectureValues.fedndtP95} ms`,
      description: 'Reports latency, SLA, fairness, throughput, overhead, and utility.',
      icon: Gauge,
    },
    {
      title: 'Optional GenAI Explanation Layer',
      value: 'explain-only',
      description: 'Future layer for interpretation. It must not generate numerical results.',
      icon: BarChart3,
    },
  ]

  function updateControl<K extends keyof SimulationControls>(key: K, value: SimulationControls[K]) {
    setControls((current) => ({ ...current, [key]: value }))
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="relative overflow-hidden border-b border-cyan-400/10 px-6 py-14">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.20),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(99,102,241,0.20),_transparent_35%)]" />
        <div className="relative mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }}>
            <p className="mb-4 inline-flex rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1 text-sm text-cyan-200">
              Browser-side FedNDT-RRM simulation demo
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-white md:text-6xl">
              Dynamic Federated Network Digital Twin Simulator
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
              Modify scenario parameters and watch the framework architecture, formulas, and QoS metrics update
              deterministically in the browser.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button
                onClick={() => setControls({ ...controls })}
                className="rounded-2xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 shadow-lg shadow-cyan-400/20"
              >
                Run simulation
              </button>
              <button
                onClick={() => setControls(defaultControls)}
                className="rounded-2xl border border-slate-700 px-5 py-3 font-semibold text-slate-200"
              >
                Reset defaults
              </button>
            </div>
          </motion.div>

          <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
            <h2 className="flex items-center gap-2 text-xl font-semibold text-white">
              <SlidersHorizontal className="h-5 w-5 text-cyan-300" />
              Scenario controls
            </h2>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <SliderControl label="Users" value={controls.numUsers} min={20} max={200} onChange={(v) => updateControl('numUsers', v)} />
              <SliderControl label="Edge/RAN nodes" value={controls.numNodes} min={2} max={8} onChange={(v) => updateControl('numNodes', v)} />
              <SliderControl label="Resources" value={controls.totalResources} min={50} max={250} onChange={(v) => updateControl('totalResources', v)} />
              <SliderControl label="Duration" value={controls.timeSteps} min={40} max={200} onChange={(v) => updateControl('timeSteps', v)} />
              <SliderControl label="Peak multiplier" value={controls.peakMultiplier} min={1} max={5} step={0.1} onChange={(v) => updateControl('peakMultiplier', v)} />
              <SliderControl label="Radio noise" value={controls.radioNoiseLevel} min={0.5} max={8} step={0.1} onChange={(v) => updateControl('radioNoiseLevel', v)} />
              <SliderControl label="Queue scale" value={controls.queueScaleMs} min={40} max={220} onChange={(v) => updateControl('queueScaleMs', v)} />
              <SliderControl label="SLA threshold" value={controls.slaThresholdMs} min={30} max={200} suffix=" ms" onChange={(v) => updateControl('slaThresholdMs', v)} />
            </div>
            <label className="mt-4 flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.035] p-4">
              <span className="text-sm text-slate-300">Incentive enabled</span>
              <input
                type="checkbox"
                checked={controls.incentiveEnabled}
                onChange={(event) => updateControl('incentiveEnabled', event.target.checked)}
                className="h-5 w-5 accent-cyan-300"
              />
            </label>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-6 py-10 md:grid-cols-4">
        {[
          ['FedNDT Avg Latency', `${round(fedndt?.avgLatencyMs ?? 0, 1)} ms`, 'mean network delay'],
          ['FedNDT p95', `${round(fedndt?.p95LatencyMs ?? 0, 1)} ms`, 'tail latency'],
          ['SLA Violation', `${round((fedndt?.slaViolationRate ?? 0) * 100, 1)}%`, 'frequency metric'],
          ['Throughput Fairness', `${round(fedndt?.throughputFairness ?? 0, 3)}`, 'Jain index'],
        ].map(([label, value, note]) => (
          <div key={label} className="rounded-3xl border border-white/10 bg-white/[0.04] p-5 shadow-2xl">
            <p className="text-sm text-slate-400">{label}</p>
            <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
            <p className="mt-2 text-sm text-slate-500">{note}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-6 pb-10 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
          <h2 className="text-2xl font-semibold text-white">Latency over time</h2>
          <p className="text-sm text-slate-400">Dynamic deterministic simulation trajectory</p>
          <div className="mt-6 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={result.latencyTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                <XAxis dataKey="step" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#020617', border: '1px solid rgba(148,163,184,0.25)' }} />
                <Legend />
                <Line type="monotone" dataKey="static" stroke="#94a3b8" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="greedy" stroke="#38bdf8" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="fedndt" stroke="#22c55e" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
          <h2 className="text-2xl font-semibold text-white">Strategy comparison</h2>
          <p className="text-sm text-slate-400">p95 latency by policy</p>
          <div className="mt-6 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartSummaries}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                <XAxis dataKey="strategy" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#020617', border: '1px solid rgba(148,163,184,0.25)' }} />
                <Bar dataKey="p95LatencyMs" fill="#22d3ee" radius={[10, 10, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-10">
        <h2 className="text-2xl font-semibold text-white">Framework architecture with live values</h2>
        <p className="mt-2 text-slate-400">Each component updates from the current simulation parameters and outputs.</p>
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {architecture.map((item) => {
            const Icon = item.icon
            return (
              <div key={item.title} className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                <Icon className="mb-4 h-7 w-7 text-cyan-300" />
                <p className="mb-2 inline-flex rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-200">
                  {item.value}
                </p>
                <h3 className="font-semibold text-white">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{item.description}</p>
              </div>
            )
          })}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-16">
        <h2 className="mb-6 flex items-center gap-2 text-2xl font-semibold text-white">
          <Calculator className="h-6 w-6 text-cyan-300" />
          Mathematical model panel
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <FormulaCard
            title="Radio capacity"
            formula={'C_i(t) = B_i(t) log2(1 + SINR_i(t))'}
            note={`Current radio noise = ${controls.radioNoiseLevel}. Capacity updates from allocated resource share and synthetic SINR.`}
          />
          <FormulaCard
            title="Queueing latency"
            formula={'rho_j(t) = lambda_j(t) / mu_j(t)\\nD_queue = scale / max(mu_j(t) - lambda_j(t), epsilon)'}
            note={`Queue scale = ${controls.queueScaleMs} ms. Higher load near capacity increases delay nonlinearly.`}
          />
          <FormulaCard
            title="Reliability / incentive"
            formula={'R_j(t) = w_f F_j + w_a A_j + w_c C_j + w_s S_j'}
            note={controls.incentiveEnabled ? 'Incentive scoring is enabled.' : 'Incentive scoring is disabled; reliability is neutralized.'}
          />
          <FormulaCard
            title="FedNDT allocation score"
            formula={'S_j = αD̂_j + βD_j + γG_j + δR_j + ηF_j\\nx_j = R_total S_j / ΣS_k'}
            note={`Weights: α=${controls.alpha}, β=${controls.beta}, γ=${controls.gamma}, δ=${controls.delta}, η=${controls.eta}.`}
          />
        </div>
      </section>

      <section className="border-t border-white/10 bg-slate-900/50 px-6 py-8">
        <div className="mx-auto max-w-7xl text-sm leading-6 text-slate-400">
          <strong className="text-slate-200">Scope note:</strong> This browser demo is a network-level
          Edge/RAN resource-management simulation. It is not a physical-layer 5G/6G waveform simulator.
          Any future GenAI layer must explain results only, not generate numerical outputs.
        </div>
      </section>
    </main>
  )
}

export default App
