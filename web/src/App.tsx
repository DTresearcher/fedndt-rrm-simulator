import { motion } from 'framer-motion'
import {
  Activity,
  BarChart3,
  BrainCircuit,
  Gauge,
  GitBranch,
  Network,
  RadioTower,
  ShieldCheck,
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

type StrategyMetric = {
  strategy: string
  avgLatency: number
  p95Latency: number
  p99Latency: number
  slaViolationRate: number
  fairness: number
}

const sampleMetrics: StrategyMetric[] = [
  {
    strategy: 'Static',
    avgLatency: 151.25,
    p95Latency: 951.0,
    p99Latency: 956.36,
    slaViolationRate: 0.164,
    fairness: 1.0,
  },
  {
    strategy: 'Greedy',
    avgLatency: 336.23,
    p95Latency: 940.2,
    p99Latency: 944.29,
    slaViolationRate: 0.361,
    fairness: 0.833,
  },
  {
    strategy: 'FedNDT',
    avgLatency: 324.9,
    p95Latency: 938.76,
    p99Latency: 940.14,
    slaViolationRate: 0.347,
    fairness: 0.862,
  },
]

const latencyTrend = [
  { step: 0, static: 28, greedy: 27, fedndt: 27 },
  { step: 20, static: 34, greedy: 36, fedndt: 35 },
  { step: 40, static: 92, greedy: 155, fedndt: 145 },
  { step: 60, static: 370, greedy: 640, fedndt: 590 },
  { step: 80, static: 210, greedy: 420, fedndt: 390 },
  { step: 100, static: 70, greedy: 95, fedndt: 88 },
]

const architecture = [
  {
    title: 'Simulated Edge/RAN Environment',
    description: 'Synthetic users, demand, mobility, radio noise, and overload conditions.',
    icon: RadioTower,
  },
  {
    title: 'Telemetry Generator',
    description: 'Creates deterministic scenario telemetry from YAML-style controls.',
    icon: Activity,
  },
  {
    title: 'Local Network Digital Twin',
    description: 'Builds local node-level state for demand, congestion, and quality.',
    icon: Network,
  },
  {
    title: 'Federated Prediction Layer',
    description: 'Lightweight FedAvg-inspired prediction abstraction.',
    icon: GitBranch,
  },
  {
    title: 'Incentive / Reliability Engine',
    description: 'Scores freshness, accuracy, consistency, and participation.',
    icon: ShieldCheck,
  },
  {
    title: 'Resource Allocation Optimizer',
    description: 'Compares static, greedy, and FedNDT-Incentive allocation.',
    icon: BrainCircuit,
  },
  {
    title: 'QoS and Utility Evaluation',
    description: 'Reports latency, SLA, fairness, throughput, overhead, and utility.',
    icon: Gauge,
  },
  {
    title: 'Optional GenAI Explanation Layer',
    description: 'Future explanation-only layer. It must not generate numerical results.',
    icon: BarChart3,
  },
]

function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="relative overflow-hidden border-b border-cyan-400/10 px-6 py-16">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.20),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(99,102,241,0.20),_transparent_35%)]" />
        <div className="relative mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
            className="max-w-4xl"
          >
            <p className="mb-4 inline-flex rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1 text-sm text-cyan-200">
              Network-level FedNDT-RRM research simulator
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-white md:text-6xl">
              Federated Network Digital Twin for Incentive-Aware Edge/RAN Resource Management
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
              A browser-side research demo for exploring deterministic scenario simulation,
              calibrated queue/radio abstractions, incentive scoring, resource allocation,
              and claim-safe QoS analysis.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button className="rounded-2xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 shadow-lg shadow-cyan-400/20">
                Run demo simulation
              </button>
              <button className="rounded-2xl border border-slate-700 px-5 py-3 font-semibold text-slate-200">
                View methodology
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-6 py-10 md:grid-cols-4">
        {[
          ['Avg Latency', '324.9 ms', 'FedNDT stress sample'],
          ['p95 Latency', '938.8 ms', 'tail-latency view'],
          ['SLA Violation', '34.7%', 'frequency metric'],
          ['Fairness', '0.862', 'Jain throughput fairness'],
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
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-white">Latency trend</h2>
              <p className="text-sm text-slate-400">Sample deterministic stress trajectory</p>
            </div>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latencyTrend}>
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
          <p className="text-sm text-slate-400">Sample p95 latency comparison</p>
          <div className="mt-6 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sampleMetrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                <XAxis dataKey="strategy" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#020617', border: '1px solid rgba(148,163,184,0.25)' }} />
                <Bar dataKey="p95Latency" fill="#22d3ee" radius={[10, 10, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-16">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-white">Framework architecture</h2>
          <p className="mt-2 text-slate-400">
            Components are mapped to the research framework and will later become interactive.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {architecture.map((item) => {
            const Icon = item.icon
            return (
              <div key={item.title} className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                <Icon className="mb-4 h-7 w-7 text-cyan-300" />
                <h3 className="font-semibold text-white">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{item.description}</p>
              </div>
            )
          })}
        </div>
      </section>

      <section className="border-t border-white/10 bg-slate-900/50 px-6 py-8">
        <div className="mx-auto max-w-7xl text-sm leading-6 text-slate-400">
          <strong className="text-slate-200">Scope note:</strong> This is a network-level Edge/RAN
          resource-management demo. It is not a physical-layer 5G/6G waveform simulator, and any
          future GenAI layer must only explain results, not generate numerical simulation outputs.
        </div>
      </section>
    </main>
  )
}

export default App
