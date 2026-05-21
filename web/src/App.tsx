import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  BrainCircuit,
  Database,
  Gauge,
  GitBranch,
  Network,
  RadioTower,
  Waves,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
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
  classifyImprovement,
  defaultControls,
  formatStrategy,
  higherIsBetterImprovement,
  lowerIsBetterImprovement,
  round,
  runSimulation,
  scenarioPresets,
  type SimulationControls,
  type StrategySummary,
} from './simulation/fedndtSimulation'

type LayerId =
  | 'environment'
  | 'traffic'
  | 'telemetry'
  | 'ndt'
  | 'prediction'
  | 'optimizer'
  | 'physics'
  | 'evaluation'

type SliderProps = {
  label: string
  value: number
  min: number
  max: number
  step?: number
  suffix?: string
  onChange: (value: number) => void
}

type ToggleProps = {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}

type LayerConfig = {
  id: LayerId
  code: string
  title: string
  subtitle: string
  icon: LucideIcon
  className: string
  formulaPreview: string
  formulaFull: string
  liveValues: Array<[string, string | number]>
  impact: string
  controls?: ReactNode
  extra?: ReactNode
  accent?: 'cyan' | 'emerald' | 'violet'
}

type StrategyMetricKey =
  | 'avgLatencyMs'
  | 'p95LatencyMs'
  | 'p99LatencyMs'
  | 'slaViolationRate'
  | 'throughputFairness'

const scenarioOptions: Array<{ value: keyof typeof scenarioPresets; label: string }> = [
  { value: 'peakTraffic', label: 'Peak traffic' },
  { value: 'unreliableStress', label: 'Unreliable stress' },
  { value: 'mobilityStress', label: 'Mobility stress' },
  { value: 'overloadStress', label: 'Overload stress' },
  { value: 'highNoiseRadio', label: 'High-noise radio' },
  { value: 'lowCapacity', label: 'Low capacity' },
]

const strategyMetricOptions: Array<{
  value: StrategyMetricKey
  label: string
  note: string
  unit: string
}> = [
  { value: 'avgLatencyMs', label: 'Average latency', note: 'mean latency by allocation policy', unit: 'ms' },
  { value: 'p95LatencyMs', label: 'p95 latency', note: '95th percentile latency by allocation policy', unit: 'ms' },
  { value: 'p99LatencyMs', label: 'p99 latency', note: '99th percentile latency by allocation policy', unit: 'ms' },
  { value: 'slaViolationRate', label: 'SLA violation rate', note: 'SLA violation percentage by allocation policy', unit: '%' },
  { value: 'throughputFairness', label: 'Throughput fairness', note: 'Jain fairness index by allocation policy', unit: 'index' },
]

function SliderControl({ label, value, min, max, step = 1, suffix = '', onChange }: SliderProps) {
  return (
    <label className="block rounded-xl border border-white/10 bg-slate-950/70 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-xs font-medium text-slate-300">{label}</span>
        <span className="rounded-full bg-cyan-400/10 px-2 py-0.5 text-[11px] font-semibold text-cyan-200">
          {step < 1 ? round(value, 2) : round(value, 0)}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-1.5 w-full accent-cyan-300"
      />
    </label>
  )
}

function ToggleControl({ label, checked, onChange }: ToggleProps) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-slate-950/70 p-3">
      <span className="text-xs font-medium text-slate-300">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-cyan-300"
      />
    </label>
  )
}

function MetricPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-cyan-300/10 bg-cyan-300/[0.06] p-2.5">
      <p className="text-[10px] text-slate-400">{label}</p>
      <p className="mt-1 truncate text-xs font-semibold text-cyan-100">{value}</p>
    </div>
  )
}

function DetailsSection({
  title,
  children,
  defaultOpen = false,
}: {
  title: string
  children: ReactNode
  defaultOpen?: boolean
}) {
  return (
    <details
      open={defaultOpen}
      className="group rounded-2xl border border-white/10 bg-slate-950/70 p-3.5"
    >
      <summary className="cursor-pointer list-none text-sm font-semibold text-white">
        <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-cyan-300/10 text-xs text-cyan-200">
          ▾
        </span>
        {title}
      </summary>
      <div className="mt-4">{children}</div>
    </details>
  )
}

function DiagramNode({
  layer,
  isActive,
  onClick,
}: {
  layer: LayerConfig
  isActive: boolean
  onClick: () => void
}) {
  const Icon = layer.icon

  const accentClass =
    layer.accent === 'emerald'
      ? 'border-emerald-300/80 bg-emerald-950/25 shadow-emerald-900/30 ring-1 ring-emerald-300/25'
      : layer.accent === 'violet'
        ? 'border-violet-300/80 bg-violet-950/25 shadow-violet-900/30 ring-1 ring-violet-300/25'
        : 'border-cyan-300/80 bg-cyan-950/25 shadow-cyan-950/30 ring-1 ring-cyan-300/25'

  return (
    <button
      type="button"
      onClick={onClick}
      className={`absolute z-20 text-left transition duration-200 ${layer.className}`}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.98, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        whileHover={{ y: -2 }}
        transition={{ duration: 0.25 }}
        className={`h-[136px] rounded-lg border bg-slate-950/95 p-3 shadow-lg backdrop-blur ${
          isActive ? accentClass : 'border-slate-400/45 shadow-black/20 opacity-[0.92]'
        }`}
      >
        <div className="flex items-start gap-2.5">
          <div
            className={`mt-0.5 rounded-md border p-2 ${
              isActive
                ? 'border-cyan-300/40 bg-cyan-300/15'
                : 'border-white/10 bg-white/[0.04]'
            }`}
          >
            <Icon className="h-4 w-4 text-cyan-200" />
          </div>
          <div className="min-w-0">
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-300">
              {layer.code}
            </p>
            <h3 className="mt-1 text-[15px] font-semibold leading-5 text-white">
              {layer.title}
            </h3>
            <p className="mt-2 line-clamp-2 text-[11px] leading-4 text-slate-400">
              {layer.subtitle}
            </p>
          </div>
        </div>
      </motion.div>
    </button>
  )
}

function strengthClass(strength: string) {
  if (strength === 'strong_improvement') return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
  if (strength === 'modest_improvement') return 'border-cyan-400/30 bg-cyan-400/10 text-cyan-200'
  if (strength === 'neutral') return 'border-slate-400/30 bg-slate-400/10 text-slate-200'
  return 'border-rose-400/30 bg-rose-400/10 text-rose-200'
}

function claimRows(fedndt: StrategySummary, greedy: StrategySummary) {
  const rows = [
    {
      metric: 'Average latency',
      improvement: lowerIsBetterImprovement(greedy.avgLatencyMs, fedndt.avgLatencyMs),
      fedndt: `${round(fedndt.avgLatencyMs, 1)} ms`,
      baseline: `${round(greedy.avgLatencyMs, 1)} ms`,
    },
    {
      metric: 'p95 latency',
      improvement: lowerIsBetterImprovement(greedy.p95LatencyMs, fedndt.p95LatencyMs),
      fedndt: `${round(fedndt.p95LatencyMs, 1)} ms`,
      baseline: `${round(greedy.p95LatencyMs, 1)} ms`,
    },
    {
      metric: 'p99 latency',
      improvement: lowerIsBetterImprovement(greedy.p99LatencyMs, fedndt.p99LatencyMs),
      fedndt: `${round(fedndt.p99LatencyMs, 1)} ms`,
      baseline: `${round(greedy.p99LatencyMs, 1)} ms`,
    },
    {
      metric: 'Latency excess',
      improvement: lowerIsBetterImprovement(greedy.avgLatencyExcessMs, fedndt.avgLatencyExcessMs),
      fedndt: `${round(fedndt.avgLatencyExcessMs, 1)} ms`,
      baseline: `${round(greedy.avgLatencyExcessMs, 1)} ms`,
    },
    {
      metric: 'Throughput fairness',
      improvement: higherIsBetterImprovement(greedy.throughputFairness, fedndt.throughputFairness),
      fedndt: `${round(fedndt.throughputFairness, 3)}`,
      baseline: `${round(greedy.throughputFairness, 3)}`,
    },
    {
      metric: 'Overhead reduction',
      improvement: fedndt.overheadReductionRatio * 100,
      fedndt: `${round(fedndt.overheadReductionRatio * 100, 1)}%`,
      baseline: '0.0%',
    },
  ]

  return rows.map((row) => ({
    ...row,
    strength: classifyImprovement(row.improvement),
  }))
}

function App() {
  const [controls, setControls] = useState<SimulationControls>(defaultControls)
  const [activePreset, setActivePreset] = useState<keyof typeof scenarioPresets>('unreliableStress')
  const [activeLayerId, setActiveLayerId] = useState<LayerId>('ndt')
  const [strategyMetric, setStrategyMetric] = useState<StrategyMetricKey>('avgLatencyMs')

  const result = useMemo(() => runSimulation(controls), [controls])

  const fedndt = result.summaries.find((summary) => summary.strategy === 'fedndt')!
  const greedy = result.summaries.find((summary) => summary.strategy === 'greedy')!
  const staticStrategy = result.summaries.find((summary) => summary.strategy === 'static')!
  const latestNodes = result.nodeSnapshots.filter((node) => node.step === result.controls.timeSteps - 1)
  const claims = claimRows(fedndt, greedy)

  const chartSummaries = result.summaries.map((summary) => ({
    strategy: formatStrategy(summary.strategy),
    avgLatencyMs: round(summary.avgLatencyMs, 1),
    p95LatencyMs: round(summary.p95LatencyMs, 1),
    p99LatencyMs: round(summary.p99LatencyMs, 1),
    slaViolationRate: round(summary.slaViolationRate * 100, 1),
    throughputFairness: round(summary.throughputFairness, 3),
  }))

  const activeStrategyMetric =
    strategyMetricOptions.find((option) => option.value === strategyMetric) ?? strategyMetricOptions[0]

  function formatChartValue(value: number | string, unit: string) {
    if (typeof value !== 'number') return value
    if (unit === 'index') return round(value, 3)
    return `${value} ${unit}`
  }

  function updateControl<K extends keyof SimulationControls>(key: K, value: SimulationControls[K]) {
    setControls((current) => ({ ...current, [key]: value }))
  }

  function applyPreset(name: keyof typeof scenarioPresets) {
    setActivePreset(name)
    setControls(scenarioPresets[name])
  }

  const activeScenarioLabel =
    scenarioOptions.find((option) => option.value === activePreset)?.label ?? 'Custom scenario'

  const layers: LayerConfig[] = [
    {
      id: 'environment',
      code: 'L01',
      title: 'Edge/RAN Environment',
      subtitle: 'Network size and resource envelope',
      icon: RadioTower,
      className: 'left-[70px] top-[190px] w-[250px]',
      formulaPreview: 'Nᵤ = users\nNₑ = Edge/RAN nodes\nR_total = resources',
      formulaFull:
        'Nᵤ = number of simulated users\nNₑ = number of Edge/RAN domains\nR_total = total available abstract resource units\nT = simulation time steps',
      liveValues: [
        ['users', result.architectureValues.users],
        ['nodes', result.architectureValues.nodes],
        ['resources', result.architectureValues.totalResources],
        ['steps', result.controls.timeSteps],
      ],
      impact: 'Defines the size of the digital twin and the resource budget shared by all allocation strategies.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="Users" value={controls.numUsers} min={20} max={220} onChange={(v) => updateControl('numUsers', v)} />
          <SliderControl label="Nodes" value={controls.numNodes} min={2} max={8} onChange={(v) => updateControl('numNodes', v)} />
          <SliderControl label="Resources" value={controls.totalResources} min={50} max={260} onChange={(v) => updateControl('totalResources', v)} />
          <SliderControl label="Steps" value={controls.timeSteps} min={40} max={220} onChange={(v) => updateControl('timeSteps', v)} />
        </div>
      ),
    },
    {
      id: 'traffic',
      code: 'L02',
      title: 'Traffic & Stress Model',
      subtitle: 'Peak load, mobility, and overload behaviour',
      icon: Waves,
      className: 'left-[490px] top-[190px] w-[250px]',
      formulaPreview: 'Dⱼ(t)=baseⱼ × peak(t)\n× mobility(t) × overloadⱼ(t)',
      formulaFull:
        'Dⱼ(t) = base demand at node j × peak load multiplier × mobility shift factor × overloaded-node multiplier.\n\nThis controls the demand process entering the NDT state.',
      liveValues: [
        ['avg demand', result.architectureValues.avgDemand],
        ['overload node', controls.overloadedNode],
        ['overload ×', controls.overloadMultiplier],
        ['mobility p', controls.mobilityShiftProbability],
      ],
      impact: 'Generates demand pressure that affects prediction, congestion risk, queue utilization, and SLA outcomes.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="Traffic intensity" value={controls.trafficIntensity} min={0.5} max={2.5} step={0.1} onChange={(v) => updateControl('trafficIntensity', v)} />
          <SliderControl label="Peak multiplier" value={controls.peakMultiplier} min={1} max={5} step={0.1} onChange={(v) => updateControl('peakMultiplier', v)} />
          <SliderControl label="Mobility probability" value={controls.mobilityShiftProbability} min={0} max={0.8} step={0.01} onChange={(v) => updateControl('mobilityShiftProbability', v)} />
          <SliderControl label="Overloaded node" value={controls.overloadedNode} min={0} max={Math.max(0, controls.numNodes - 1)} onChange={(v) => updateControl('overloadedNode', v)} />
          <SliderControl label="Overload multiplier" value={controls.overloadMultiplier} min={1} max={5} step={0.1} onChange={(v) => updateControl('overloadMultiplier', v)} />
          <SliderControl label="Greedy delay" value={controls.greedyDelaySteps} min={0} max={12} onChange={(v) => updateControl('greedyDelaySteps', v)} />
        </div>
      ),
    },
    {
      id: 'telemetry',
      code: 'L03',
      title: 'Telemetry Reliability',
      subtitle: 'Stale/noisy reporting and trust score',
      icon: Activity,
      className: 'left-[910px] top-[190px] w-[250px]',
      formulaPreview: 'Fⱼ = exp(-Δt/τ)\nAⱼ = 1 - |yⱼ-ŷⱼ| / max(yⱼ,ε)',
      formulaFull:
        'Fⱼ(t) = freshness score\nAⱼ(t) = prediction accuracy score\nCⱼ(t) = reporting consistency score\nSⱼ(t) = participation score\n\nRⱼ(t) combines these into a reliability/incentive score.',
      liveValues: [
        ['unreliable node', controls.unreliableNode],
        ['avg reliability', result.architectureValues.avgReliability],
        ['stale p', controls.staleUpdateProbability],
        ['noise p', controls.reportingNoiseProbability],
      ],
      impact: 'Affects whether FedNDT trusts local reports and how reliability contributes to allocation.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="Unreliable node" value={controls.unreliableNode} min={0} max={Math.max(0, controls.numNodes - 1)} onChange={(v) => updateControl('unreliableNode', v)} />
          <SliderControl label="Stale probability" value={controls.staleUpdateProbability} min={0} max={0.8} step={0.01} onChange={(v) => updateControl('staleUpdateProbability', v)} />
          <SliderControl label="Report noise probability" value={controls.reportingNoiseProbability} min={0} max={0.8} step={0.01} onChange={(v) => updateControl('reportingNoiseProbability', v)} />
          <ToggleControl label="Enable incentive scoring" checked={controls.incentiveEnabled} onChange={(v) => updateControl('incentiveEnabled', v)} />
        </div>
      ),
    },
    {
      id: 'ndt',
      code: 'L04',
      title: 'Local Network Digital Twin Core',
      subtitle: 'Live digital state of each Edge/RAN domain',
      icon: Database,
      className: 'left-[455px] top-[380px] w-[330px]',
      formulaPreview: 'stateⱼ(t) = {Dⱼ, ŷⱼ, SINRⱼ, Cⱼ, Rⱼ, Gⱼ}',
      formulaFull:
        'The local NDT state contains demand Dⱼ, predicted demand ŷⱼ, synthetic SINR, estimated capacity Cⱼ, reliability Rⱼ, and congestion risk Gⱼ.\n\nThis is the central representation used by prediction, allocation, and evaluation.',
      liveValues: [
        ['avg capacity', `${round(fedndt.avgCapacityMbps, 2)} Mbps`],
        ['queue ρ', round(fedndt.avgQueueRho, 3)],
        ['prediction MAE', round(fedndt.avgPredictionMae, 2)],
        ['FedNDT p95', `${round(fedndt.p95LatencyMs, 1)} ms`],
      ],
      impact: 'Acts as the central NDT representation connecting telemetry, prediction, reliability, allocation, and physics.',
      accent: 'cyan',
      extra: (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[580px] text-left text-xs">
            <thead className="border-b border-white/10 text-slate-400">
              <tr>
                <th className="py-2 pr-3">Node</th>
                <th className="py-2 pr-3">Demand</th>
                <th className="py-2 pr-3">Predicted</th>
                <th className="py-2 pr-3">SINR dB</th>
                <th className="py-2 pr-3">Capacity</th>
                <th className="py-2 pr-3">Reliability</th>
                <th className="py-2 pr-3">Congestion</th>
              </tr>
            </thead>
            <tbody>
              {latestNodes.map((node) => (
                <tr key={node.nodeId} className="border-b border-white/5">
                  <td className="py-2 pr-3 font-semibold text-white">{node.nodeId}</td>
                  <td className="py-2 pr-3">{round(node.demand, 2)}</td>
                  <td className="py-2 pr-3">{round(node.predictedDemand, 2)}</td>
                  <td className="py-2 pr-3">{round(node.radioQualityDb, 2)}</td>
                  <td className="py-2 pr-3">{round(node.capacityMbps, 2)} Mbps</td>
                  <td className="py-2 pr-3">{round(node.reliability, 3)}</td>
                  <td className="py-2 pr-3">{round(node.congestionRisk, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    },
    {
      id: 'prediction',
      code: 'L05',
      title: 'Federated Prediction',
      subtitle: 'FedAvg-inspired lightweight demand estimation',
      icon: GitBranch,
      className: 'left-[70px] top-[580px] w-[250px]',
      formulaPreview: 'θ_global = Σⱼ(nⱼ/N)θⱼ\nŷⱼ(t+1)=smoothed demand',
      formulaFull:
        'θ_global^(r+1) = Σⱼ(nⱼ/N)θⱼ^r\n\nIn this browser demo, the model uses a lightweight deterministic demand-history prediction as a transparent FedAvg-inspired abstraction.',
      liveValues: [
        ['α predicted', controls.alpha],
        ['β current', controls.beta],
        ['MAE', round(fedndt.avgPredictionMae, 2)],
        ['greedy delay', controls.greedyDelaySteps],
      ],
      impact: 'Controls how strongly predicted and current demand influence the FedNDT allocation score.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="α predicted demand" value={controls.alpha} min={0} max={1} step={0.01} onChange={(v) => updateControl('alpha', v)} />
          <SliderControl label="β current demand" value={controls.beta} min={0} max={1} step={0.01} onChange={(v) => updateControl('beta', v)} />
          <SliderControl label="Greedy observation delay" value={controls.greedyDelaySteps} min={0} max={12} onChange={(v) => updateControl('greedyDelaySteps', v)} />
        </div>
      ),
    },
    {
      id: 'optimizer',
      code: 'L06',
      title: 'Incentive-Aware Optimizer',
      subtitle: 'Resource allocation score and policy comparison',
      icon: BrainCircuit,
      className: 'left-[360px] top-[580px] w-[250px]',
      formulaPreview: 'Sⱼ=αD̂ⱼ+βDⱼ+γGⱼ+δRⱼ+ηFⱼ\nxⱼ=R_total Sⱼ / ΣSₖ',
      formulaFull:
        'Sⱼ = αD̂ⱼ + βDⱼ + γGⱼ + δRⱼ + ηFⱼ\nxⱼ = R_total × Sⱼ / ΣₖSₖ\n\nThe allocation score combines predicted demand, current demand, congestion risk, reliability, and fairness compensation.',
      liveValues: [
        ['γ congestion', controls.gamma],
        ['δ reliability', controls.delta],
        ['η fairness', controls.eta],
        ['FedNDT fairness', round(fedndt.throughputFairness, 3)],
      ],
      impact: 'Determines whether FedNDT behaves more demand-reactive, congestion-aware, reliability-aware, or fairness-aware.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="γ congestion risk" value={controls.gamma} min={0} max={1} step={0.01} onChange={(v) => updateControl('gamma', v)} />
          <SliderControl label="δ reliability score" value={controls.delta} min={0} max={1} step={0.01} onChange={(v) => updateControl('delta', v)} />
          <SliderControl label="η fairness compensation" value={controls.eta} min={0} max={1} step={0.01} onChange={(v) => updateControl('eta', v)} />
        </div>
      ),
    },
    {
      id: 'physics',
      code: 'L07',
      title: 'Network Physics Abstraction',
      subtitle: 'Capacity, queueing pressure, and latency composition',
      icon: Network,
      className: 'left-[650px] top-[580px] w-[250px]',
      formulaPreview: 'Cᵢ=Bᵢlog₂(1+SINRᵢ)\nρⱼ=λⱼ/μⱼ\nD=D_base+D_radio+D_queue+D_backhaul',
      formulaFull:
        'Cᵢ(t) = Bᵢ(t)log₂(1 + SINRᵢ(t))\nρⱼ(t) = λⱼ(t) / μⱼ(t)\nDⱼ(t) = D_base + D_radio + D_queue + D_backhaul\n\nThis is a calibrated network-level abstraction, not a physical-layer 5G/6G waveform simulator.',
      liveValues: [
        ['radio noise', controls.radioNoiseLevel],
        ['queue scale', controls.queueScaleMs],
        ['service calibration', controls.serviceCalibration],
        ['SLA threshold', `${controls.slaThresholdMs} ms`],
      ],
      impact: 'Transforms demand and allocation into latency, throughput, SLA, and tail-latency behaviour.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="Radio noise" value={controls.radioNoiseLevel} min={0.5} max={8} step={0.1} onChange={(v) => updateControl('radioNoiseLevel', v)} />
          <SliderControl label="Queue delay scale" value={controls.queueScaleMs} min={40} max={240} onChange={(v) => updateControl('queueScaleMs', v)} />
          <SliderControl label="Service calibration" value={controls.serviceCalibration} min={0.8} max={3.2} step={0.1} onChange={(v) => updateControl('serviceCalibration', v)} />
          <SliderControl label="Radio delay scale" value={controls.radioDelayScale} min={1} max={10} step={0.1} onChange={(v) => updateControl('radioDelayScale', v)} />
          <SliderControl label="SLA threshold" value={controls.slaThresholdMs} min={30} max={200} suffix=" ms" onChange={(v) => updateControl('slaThresholdMs', v)} />
        </div>
      ),
    },
    {
      id: 'evaluation',
      code: 'L08',
      title: 'QoS & Claim Evaluation',
      subtitle: 'Latency, fairness, SLA, and claim-safe interpretation',
      icon: Gauge,
      className: 'left-[940px] top-[580px] w-[250px]',
      formulaPreview: 'Improvement%=(baseline−FedNDT)/|baseline|×100\nJ(x)=(Σxᵢ)²/(nΣxᵢ²)',
      formulaFull:
        'Improvement% = (baseline − FedNDT) / |baseline| × 100\nJ(x) = (Σxᵢ)² / (nΣxᵢ²)\n\nClaim strength is classified as strong improvement, modest improvement, neutral, or regression.',
      liveValues: [
        ['FedNDT avg', `${round(fedndt.avgLatencyMs, 1)} ms`],
        ['Greedy avg', `${round(greedy.avgLatencyMs, 1)} ms`],
        ['Static avg', `${round(staticStrategy.avgLatencyMs, 1)} ms`],
        ['gains', `${claims.filter((claim) => claim.strength.includes('improvement')).length}/6`],
      ],
      impact: 'Prevents overclaiming by classifying improvements instead of only showing raw percentages.',
      accent: 'emerald',
      extra: (
        <div className="space-y-3">
          {claims.map((claim) => (
            <div key={claim.metric} className="rounded-xl border border-white/10 bg-slate-950/70 p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold text-white">{claim.metric}</p>
                  <p className="mt-1 text-[11px] text-slate-500">
                    FedNDT {claim.fedndt} vs Greedy {claim.baseline}
                  </p>
                </div>
                <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold ${strengthClass(claim.strength)}`}>
                  {claim.strength.replace('_', ' ')} · {round(claim.improvement, 1)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      ),
    },
  ]

  const activeLayer = layers.find((layer) => layer.id === activeLayerId) ?? layers[0]
  const ActiveIcon = activeLayer.icon

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="border-b border-cyan-400/10 bg-slate-950 px-6 py-5">
        <div className="mx-auto w-full max-w-[1920px]">
          <div>
            <p className="mb-2 inline-flex rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1 text-xs font-medium text-cyan-200">
              Architecture-first Network Digital Twin
            </p>
            <h1 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
              Living FedNDT-RRM Framework Simulator
            </h1>
            <p className="mt-3 max-w-5xl text-sm leading-6 text-slate-400 md:text-base">
              A clean NDT canvas with clickable layers. Select a layer to configure its parameters,
              inspect formulas, view live state, and understand downstream QoS impact.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1920px] gap-4 px-6 py-5 md:grid-cols-4">
        {[
          ['FedNDT Average Latency', `${round(fedndt.avgLatencyMs, 1)} ms`, 'mean delay'],
          ['FedNDT p95 / p99', `${round(fedndt.p95LatencyMs, 1)} / ${round(fedndt.p99LatencyMs, 1)} ms`, 'tail latency'],
          ['SLA Violation Rate', `${round(fedndt.slaViolationRate * 100, 1)}%`, 'frequency'],
          ['Throughput Fairness', `${round(fedndt.throughputFairness, 3)}`, 'Jain index'],
        ].map(([label, value, note]) => (
          <div key={label} className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs font-medium text-slate-400">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
            <p className="mt-1 text-[11px] text-slate-500">{note}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto grid w-full max-w-[1760px] gap-5 px-6 pb-8 2xl:grid-cols-[minmax(0,1fr)_430px]">
        <div>
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-white md:text-3xl">Interactive FedNDT framework canvas</h2>
            <p className="mt-2 max-w-5xl text-sm leading-6 text-slate-400">
              The diagram remains clean. Detailed controls and formulas open in the layer inspector.
            </p>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-950/70">
            <div className="relative h-[760px] min-w-[1240px] overflow-hidden bg-[#020617]">
              <svg className="pointer-events-none absolute inset-0 z-0 h-full w-full" viewBox="0 0 1240 760" preserveAspectRatio="none">
                <defs>
                  <marker id="arrowClean" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth">
                    <path d="M0,0 L0,10 L10,5 z" fill="rgba(226,232,240,0.9)" />
                  </marker>
                  <marker id="arrowSecondary" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth">
                    <path d="M0,0 L0,9 L9,4.5 z" fill="rgba(103,232,249,0.62)" />
                  </marker>

                </defs>

                <g stroke="rgba(103,232,249,0.42)" strokeWidth="1.35" fill="none" strokeLinecap="square" strokeLinejoin="miter" markerEnd="url(#arrowSecondary)">
                  <path d="M195 336 V420 H445" />
                  <path d="M620 336 V370" />
                  <path d="M1035 336 V420 H795" />
                  <path d="M455 476 H195 V570" />
                  <path d="M565 516 V545 H485 V570" />
                  <path d="M685 516 V545 H775 V570" />
                </g>

                <g stroke="rgba(226,232,240,0.82)" strokeWidth="1.8" fill="none" strokeLinecap="square" strokeLinejoin="miter" markerEnd="url(#arrowClean)">
                  <path d="M620 142 V180" />
                  <path d="M320 258 H480" />
                  <path d="M740 258 H900" />
                  <path d="M320 648 H350" />
                  <path d="M610 648 H640" />
                  <path d="M900 648 H930" />
                </g>
              </svg>

              <div className="absolute left-[445px] top-[24px] z-10 w-[350px] rounded-lg border border-dashed border-cyan-200/60 bg-slate-950/95 px-4 py-3 text-slate-100">
                <label className="block font-mono text-sm font-semibold leading-5">
                  Scenario Configuration
                </label>
                <select
                  value={activePreset}
                  onChange={(event) => applyPreset(event.target.value as keyof typeof scenarioPresets)}
                  className="mt-2 w-full rounded-md border border-cyan-300/30 bg-slate-900 px-3 py-2 text-sm font-semibold text-cyan-100 outline-none focus:border-cyan-200"
                  aria-label="Scenario configuration"
                >
                  {scenarioOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <p className="truncate text-xs text-slate-400">{activeScenarioLabel}</p>
                  <button
                    type="button"
                    onClick={() => applyPreset(activePreset)}
                    className="rounded-md border border-white/10 px-2.5 py-1 text-[11px] font-bold text-slate-200"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {layers.map((layer) => (
                <DiagramNode
                  key={layer.id}
                  layer={layer}
                  isActive={activeLayerId === layer.id}
                  onClick={() => setActiveLayerId(layer.id)}
                />
              ))}
            </div>
          </div>

          <div className="mt-6 grid min-w-0 gap-6 xl:grid-cols-2">
            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-2xl font-semibold text-white">Latency over time</h2>
              <p className="text-sm text-slate-400">Dynamic deterministic simulation trajectory.</p>
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.latencyTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="step" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" tickFormatter={(value) => `${value} ms`} />
                    <Tooltip
                      contentStyle={{ background: '#020617', border: '1px solid rgba(148,163,184,0.25)' }}
                      formatter={(value) => [`${value} ms`, 'Latency']}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="static" stroke="#94a3b8" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="greedy" stroke="#38bdf8" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="fedndt" stroke="#22c55e" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-2xl font-semibold text-white">Strategy comparison</h2>
                  <p className="text-sm text-slate-400">
                    {activeStrategyMetric.note}. Unit: {activeStrategyMetric.unit}.
                  </p>
                </div>
                <label className="min-w-[220px]">
                  <span className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Metric
                  </span>
                  <select
                    value={strategyMetric}
                    onChange={(event) => setStrategyMetric(event.target.value as StrategyMetricKey)}
                    className="mt-2 w-full rounded-xl border border-cyan-300/20 bg-slate-900 px-3 py-2 text-sm font-semibold text-white outline-none focus:border-cyan-300"
                  >
                    {strategyMetricOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartSummaries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="strategy" stroke="#94a3b8" />
                    <YAxis
                      stroke="#94a3b8"
                      tickFormatter={(value) => String(formatChartValue(value, activeStrategyMetric.unit))}
                    />
                    <Tooltip
                      contentStyle={{ background: '#020617', border: '1px solid rgba(148,163,184,0.25)' }}
                      formatter={(value) => [
                        formatChartValue(value as number | string, activeStrategyMetric.unit),
                        activeStrategyMetric.label,
                      ]}
                    />
                    <Bar
                      dataKey={strategyMetric}
                      name={activeStrategyMetric.label}
                      fill="#22d3ee"
                      radius={[10, 10, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        <aside className="2xl:sticky 2xl:top-5 2xl:self-start">
          <div className="max-h-[calc(100vh-2.5rem)] overflow-y-auto rounded-[2rem] border border-white/10 bg-white/[0.04] p-4 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-3">
                <ActiveIcon className="h-6 w-6 text-cyan-200" />
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-300">
                  {activeLayer.code} Layer Inspector
                </p>
                <h2 className="mt-1 text-xl font-semibold text-white">{activeLayer.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">{activeLayer.subtitle}</p>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <DetailsSection title="Mathematical model" defaultOpen>
                <pre className="whitespace-pre-wrap rounded-2xl border border-white/10 bg-black/25 p-4 text-xs leading-6 text-slate-100">
                  {activeLayer.formulaFull}
                </pre>
              </DetailsSection>

              <DetailsSection title="Live values" defaultOpen>
                <div className="grid grid-cols-2 gap-2">
                  {activeLayer.liveValues.map(([label, value]) => (
                    <MetricPill key={label} label={label} value={value} />
                  ))}
                </div>
              </DetailsSection>

              {activeLayer.controls ? (
                <DetailsSection title="Layer parameters" defaultOpen>
                  {activeLayer.controls}
                </DetailsSection>
              ) : null}

              {activeLayer.extra ? (
                <DetailsSection title={activeLayer.id === 'evaluation' ? 'Claim-safe details' : 'Layer details'} defaultOpen>
                  {activeLayer.extra}
                </DetailsSection>
              ) : null}

              <DetailsSection title="Downstream impact" defaultOpen>
                <p className="text-sm leading-6 text-slate-300">{activeLayer.impact}</p>
              </DetailsSection>
            </div>
          </div>
        </aside>
      </section>

      <section className="border-t border-white/10 bg-slate-900/50 px-6 py-8">
        <div className="mx-auto max-w-[1920px] text-sm leading-6 text-slate-400">
          <strong className="text-slate-200">Scope note:</strong> This is a browser-side,
          network-level Edge/RAN resource-management simulation. It is not a physical-layer 5G/6G
          waveform simulator. GenAI, if added later, must explain results only and must not generate
          numerical simulation outputs.
        </div>
      </section>
    </main>
  )
}

export default App
