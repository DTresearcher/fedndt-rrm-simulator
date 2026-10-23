import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import {
  BrainCircuit,
  Database,
  Gauge,
  GitBranch,
  Network,
  RadioTower,
  ShieldAlert,
  Waves,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'
import { useDashboardInteractionState } from './dashboardInteraction'
import {
  calculateImprovement,
  classifyImprovement,
  formatMetricValue,
  formatStrategy,
  metricConfig,
  round,
  runSimulation,
  scenarioPresets,
  strategyCapabilities,
  strategyOrder,
  type MetricKey,
  type SimulationControls,
  type Strategy,
  type StrategySummary,
} from './simulation/fedndtSimulation'

type LayerId =
  | 'environment'
  | 'telemetry'
  | 'federated'
  | 'ndt'
  | 'incentive'
  | 'action'
  | 'baseline'
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
  formula: string
  liveValues: Array<[string, string | number]>
  impact: string
  controls?: ReactNode
  extra?: ReactNode
  accent?: 'cyan' | 'emerald' | 'violet'
}

const scenarioOptions: Array<{ value: keyof typeof scenarioPresets; label: string }> = [
  { value: 'normalTraffic', label: 'Normal traffic' },
  { value: 'peakTraffic', label: 'Peak traffic' },
  { value: 'unreliableTelemetry', label: 'Unreliable telemetry' },
  { value: 'nonIidBehavior', label: 'Non-IID node behaviour' },
  { value: 'dropoutStraggler', label: 'Node dropout / straggler' },
  { value: 'highMobility', label: 'High mobility' },
  { value: 'congestionStress', label: 'Congestion stress' },
  { value: 'lowQualityContributor', label: 'Low-quality contributor / manipulation' },
]

const strategyMetricOptions = Object.entries(metricConfig).map(([value, config]) => ({
  value: value as MetricKey,
  ...config,
}))

const lineStrategies: Strategy[] = ['static', 'greedy', 'centralized', 'flOnly', 'ndtOnly', 'fndtNoIncentive', 'fedndt']
const ndtStrategies: Strategy[] = ['ndtOnly', 'fndtNoIncentive', 'fedndt']
const flStrategies: Strategy[] = ['flOnly', 'fndtNoIncentive', 'fedndt']

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

function DetailsSection({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  return (
    <details open={defaultOpen} className="group rounded-2xl border border-white/10 bg-slate-950/70 p-3.5">
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

function getSummary(summaries: StrategySummary[], strategy: Strategy) {
  return summaries.find((summary) => summary.strategy === strategy)!
}

function getCapability(strategy: Strategy) {
  return strategyCapabilities.find((capability) => capability.strategy === strategy)!
}

function isMetricApplicable(metric: MetricKey, strategy: Strategy) {
  const capability = getCapability(strategy)
  if (metric === 'twinFidelity' || metric === 'twinError') return capability.ndt
  if (metric === 'flLoss' || metric === 'convergenceRounds' || metric === 'modelAccuracy') return capability.fl
  if (metric === 'participationRate' || metric === 'contributionQuality') return capability.fl || capability.incentive
  if (metric === 'rewardVariance') return capability.incentive || strategy === 'fndtNoIncentive'
  return true
}

type StrategyInteractionProps = {
  selectedStrategies: Strategy[]
  hoveredStrategy: Strategy | null
  toggleStrategySelection: (strategy: Strategy, multiSelect?: boolean) => void
  setHoveredStrategy: (strategy: Strategy | null) => void
  getStrategyOpacity: (strategy: Strategy) => number
}

type TooltipPayload = {
  dataKey?: string | number
  name?: string | number
  value?: string | number
  color?: string
  payload?: Record<string, unknown>
}

type MetricTooltipProps = {
  active?: boolean
  payload?: TooltipPayload[]
  label?: string | number
  metric: MetricKey
  metricValue?: number
  strategy?: Strategy
  claimClassification?: string | null
  summaries?: StrategySummary[]
}

const clickableChartStyle = { cursor: 'pointer' }

function isStrategy(value: unknown): value is Strategy {
  return typeof value === 'string' && strategyOrder.includes(value as Strategy)
}

function strategyColor(strategy: Strategy) {
  return getCapability(strategy).color
}

function metricDirectionText(metric: MetricKey) {
  return metricConfig[metric].direction === 'lower' ? 'lower is better' : 'higher is better'
}

function strategyRole(strategy: Strategy) {
  if (strategy === 'static' || strategy === 'greedy') return 'heuristic baseline'
  if (strategy === 'flOnly' || strategy === 'ndtOnly' || strategy === 'fndtNoIncentive') return 'ablation'
  if (strategy === 'fedndt') return 'proposed'
  return 'research baseline'
}

function getChartEventMultiSelect(event: unknown) {
  if (!event || typeof event !== 'object') return false
  const candidate = event as { ctrlKey?: boolean; metaKey?: boolean }
  return Boolean(candidate.ctrlKey || candidate.metaKey)
}

function getPayloadStrategy(payload?: TooltipPayload[]) {
  const record = payload?.find((item) => isStrategy(item.payload?.strategyId) || isStrategy(item.dataKey))
  const strategyId = record?.payload?.strategyId ?? record?.dataKey
  return isStrategy(strategyId) ? strategyId : null
}

function MetricTooltip({ active, payload, label, metric, metricValue, strategy, claimClassification, summaries }: MetricTooltipProps) {
  if (!active) return null
  const selectedStrategy = strategy ?? getPayloadStrategy(payload)
  const focusedPayloadValue = payload?.find((item) => item.dataKey === selectedStrategy)?.value
  const value = metricValue ?? (focusedPayloadValue !== undefined
    ? Number(focusedPayloadValue)
    : (payload?.reduce((sum, item) => sum + Number(item.value ?? 0), 0) ?? 0))
  const config = metricConfig[metric]
  const inferredClaim =
    claimClassification ??
    (summaries && selectedStrategy && selectedStrategy !== 'fedndt' && isMetricApplicable(metric, selectedStrategy) && isMetricApplicable(metric, 'fedndt')
      ? classifyImprovement(
          calculateImprovement(
            getSummary(summaries, selectedStrategy)[metric] as number,
            getSummary(summaries, 'fedndt')[metric] as number,
            config.direction,
          ),
        ).replace('_', ' ')
      : null)

  return (
    <div className="rounded-xl border border-slate-500/40 bg-slate-950/95 p-3 text-xs shadow-2xl">
      <p className="font-semibold text-white">
        {selectedStrategy ? formatStrategy(selectedStrategy) : label}
      </p>
      <p className="mt-1 text-slate-300">
        {config.label}: <span className="font-semibold text-cyan-100">{formatMetricValue(value, metric)}</span>
      </p>
      <p className="mt-1 text-slate-500">Direction: {metricDirectionText(metric)}</p>
      <p className="mt-1 text-slate-500">Unit: {config.unit}</p>
      {inferredClaim ? <p className="mt-1 text-slate-500">Claim: {inferredClaim}</p> : null}
    </div>
  )
}

function StrategyLegend({
  strategies,
  selectedStrategies,
  hoveredStrategy,
  toggleStrategySelection,
  setHoveredStrategy,
  getStrategyOpacity,
}: StrategyInteractionProps & { strategies: Strategy[] }) {
  return (
    <div className="mt-4 flex flex-wrap gap-2" role="list" aria-label="Strategy legend">
      {strategies.map((strategy) => {
        const selected = selectedStrategies.includes(strategy)
        const hovered = hoveredStrategy === strategy
        return (
          <button
            key={strategy}
            type="button"
            onClick={(event) => toggleStrategySelection(strategy, event.metaKey || event.ctrlKey)}
            onMouseEnter={() => setHoveredStrategy(strategy)}
            onMouseLeave={() => setHoveredStrategy(null)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                toggleStrategySelection(strategy, event.metaKey || event.ctrlKey)
              }
            }}
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold transition ${
              selected || hovered
                ? 'border-cyan-200/80 bg-cyan-300/15 text-white'
                : 'border-white/10 bg-slate-950/70 text-slate-300'
            }`}
            style={{ opacity: getStrategyOpacity(strategy) }}
            aria-pressed={selected}
          >
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: strategyColor(strategy) }} />
            {formatStrategy(strategy)}
          </button>
        )
      })}
    </div>
  )
}

function FilterHint({
  selectedStrategies,
  clearSelection,
}: {
  selectedStrategies: Strategy[]
  clearSelection: () => void
}) {
  return (
    <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-cyan-300/10 bg-slate-950/60 p-3 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between">
      <span>Click bars, lines, points, table rows, or legends to focus a strategy. Cmd/Ctrl + click adds another strategy.</span>
      <button
        type="button"
        onClick={clearSelection}
        className="w-fit rounded-lg border border-cyan-300/30 px-3 py-1.5 font-semibold text-cyan-100 disabled:cursor-not-allowed disabled:opacity-40"
        disabled={!selectedStrategies.length}
      >
        Show all
      </button>
    </div>
  )
}

function App() {
  const [controls, setControls] = useState<SimulationControls>(scenarioPresets.unreliableTelemetry)
  const [activeLayerId, setActiveLayerId] = useState<LayerId>('baseline')
  const [claimBaseline, setClaimBaseline] = useState<Strategy>('centralized')
  const interaction = useDashboardInteractionState('avgLatencyMs', 'unreliableTelemetry')
  const {
    selectedStrategies,
    selectedMetric,
    selectedScenario,
    hoveredStrategy,
    setSelectedMetric,
    setSelectedScenario,
    toggleStrategySelection,
    setHoveredStrategy,
    clearSelection,
    getStrategyOpacity,
  } = interaction
  const activePreset = selectedScenario as keyof typeof scenarioPresets

  const result = useMemo(() => runSimulation(controls), [controls])
  const fedndt = getSummary(result.summaries, 'fedndt')
  const centralized = getSummary(result.summaries, 'centralized')
  const greedy = getSummary(result.summaries, 'greedy')
  const latestNodes = result.nodeSnapshots.filter((node) => node.step === result.controls.timeSteps - 1)
  const focusedStrategies = selectedStrategies.length ? selectedStrategies : strategyOrder
  const primaryFocusedStrategy = selectedStrategies[0] ?? 'fedndt'
  const focusedSummary = getSummary(result.summaries, primaryFocusedStrategy)
  const incentiveStrategy =
    focusedStrategies.find((strategy) => strategy === 'fedndt' || strategy === 'fndtNoIncentive') ?? 'fedndt'
  const incentiveSummary = getSummary(result.summaries, incentiveStrategy)

  const activeMetric = metricConfig[selectedMetric]
  const chartSummaries = result.summaries.map((summary) => ({
    strategy: formatStrategy(summary.strategy),
    strategyId: summary.strategy,
    value: round(summary[selectedMetric] as number, activeMetric.digits ?? 2),
  }))

  const claimMetrics: MetricKey[] = [
    'avgLatencyMs',
    'p95LatencyMs',
    'communicationOverhead',
    'privacyExposure',
    'twinFidelity',
    'flLoss',
    'jainFairness',
    'participationRate',
    'rewardVariance',
    'energyConsumption',
    'slaViolationRate',
  ]

  const selectedBaseline =
    selectedStrategies.length === 1 && selectedStrategies[0] !== 'fedndt'
      ? selectedStrategies[0]
      : claimBaseline
  const baselineSummary = getSummary(result.summaries, selectedBaseline)
  const claims = claimMetrics
    .filter((metric) => isMetricApplicable(metric, selectedBaseline) && isMetricApplicable(metric, 'fedndt'))
    .map((metric) => {
      const config = metricConfig[metric]
      const baselineValue = baselineSummary[metric] as number
      const proposedValue = fedndt[metric] as number
      const improvement = calculateImprovement(baselineValue, proposedValue, config.direction)
      return {
        metric,
        label: config.label,
        improvement,
        strength: classifyImprovement(improvement),
        baselineValue,
        proposedValue,
      }
    })

  function updateControl<K extends keyof SimulationControls>(key: K, value: SimulationControls[K]) {
    setControls((current) => ({ ...current, [key]: value }))
  }

  function applyPreset(name: keyof typeof scenarioPresets) {
    setSelectedScenario(name)
    setControls(scenarioPresets[name])
  }

  function handleStrategyClick(strategy: Strategy, event?: unknown) {
    toggleStrategySelection(strategy, getChartEventMultiSelect(event))
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') clearSelection()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [clearSelection])

  const activeScenarioLabel =
    scenarioOptions.find((option) => option.value === activePreset)?.label ?? 'Custom scenario'
  const strategyInteraction = {
    selectedStrategies,
    hoveredStrategy,
    toggleStrategySelection,
    setHoveredStrategy,
    getStrategyOpacity,
  }

  const layers: LayerConfig[] = [
    {
      id: 'environment',
      code: 'L01',
      title: 'Physical 5G/6G + Edge/RAN Environment',
      subtitle: 'Network size, abstract radio resources, and service calibration.',
      icon: RadioTower,
      className: 'left-[70px] top-[190px] w-[250px]',
      formula: 'N_u = users\nN_e = Edge/RAN nodes\nR_total = abstract resource units\nC_i = B_i log2(1 + SINR_i)',
      liveValues: [
        ['users', result.architectureValues.users],
        ['nodes', result.architectureValues.nodes],
        ['resources', result.architectureValues.totalResources],
        ['avg capacity', `${result.architectureValues.avgCapacityMbps} Mbps`],
      ],
      impact: 'Defines the deterministic resource envelope used by every baseline and ablation.',
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
      id: 'telemetry',
      code: 'L02',
      title: 'Telemetry, Traffic, Mobility, and Reliability Model',
      subtitle: 'Peak load, stale reports, noise, mobility, and contributor quality.',
      icon: Waves,
      className: 'left-[490px] top-[190px] w-[250px]',
      formula: 'D_j(t)=base_j x peak(t) x mobility(t) x overload_j(t)\nA_j=1-|D_j-Dhat_j|/max(D_j,e)',
      liveValues: [
        ['avg demand', result.architectureValues.avgDemand],
        ['unreliable node', controls.unreliableNode],
        ['stale p', controls.staleUpdateProbability],
        ['noise p', controls.reportingNoiseProbability],
      ],
      impact: 'Stressors degrade twin fidelity, FL convergence, participation, and QoS in different ways.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="Traffic intensity" value={controls.trafficIntensity} min={0.5} max={2.5} step={0.1} onChange={(v) => updateControl('trafficIntensity', v)} />
          <SliderControl label="Peak multiplier" value={controls.peakMultiplier} min={1} max={5} step={0.1} onChange={(v) => updateControl('peakMultiplier', v)} />
          <SliderControl label="Mobility probability" value={controls.mobilityShiftProbability} min={0} max={0.8} step={0.01} onChange={(v) => updateControl('mobilityShiftProbability', v)} />
          <SliderControl label="Overload multiplier" value={controls.overloadMultiplier} min={1} max={5} step={0.1} onChange={(v) => updateControl('overloadMultiplier', v)} />
          <SliderControl label="Stale probability" value={controls.staleUpdateProbability} min={0} max={0.8} step={0.01} onChange={(v) => updateControl('staleUpdateProbability', v)} />
          <SliderControl label="Report noise probability" value={controls.reportingNoiseProbability} min={0} max={0.8} step={0.01} onChange={(v) => updateControl('reportingNoiseProbability', v)} />
        </div>
      ),
    },
    {
      id: 'federated',
      code: 'L03',
      title: 'Federated Local Learning / Aggregation',
      subtitle: 'Model-update sharing with dropout, non-IID, and low-quality effects.',
      icon: GitBranch,
      className: 'left-[910px] top-[190px] w-[250px]',
      formula: 'theta_global = sum_j (n_j/N) theta_j\nFL loss degrades with dropout, non-IID severity, and contributor quality.',
      liveValues: [
        ['FL-only loss', round(getSummary(result.summaries, 'flOnly').flLoss, 3)],
        ['FNDT loss', round(fedndt.flLoss, 3)],
        ['FNDT rounds', fedndt.convergenceRounds],
        ['participation', `${round(fedndt.participationRate, 1)}%`],
      ],
      impact: 'FL reduces raw-data sharing but can converge slowly under severe non-IID or dropout.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="Participant dropout" value={controls.participantDropoutRate} min={0} max={0.7} step={0.01} onChange={(v) => updateControl('participantDropoutRate', v)} />
          <SliderControl label="Contribution variation" value={controls.contributionQualityVariation} min={0} max={0.8} step={0.01} onChange={(v) => updateControl('contributionQualityVariation', v)} />
          <SliderControl label="Low-quality contributors" value={controls.lowQualityContributorRate} min={0} max={0.7} step={0.01} onChange={(v) => updateControl('lowQualityContributorRate', v)} />
        </div>
      ),
    },
    {
      id: 'ndt',
      code: 'L04',
      title: 'Network Digital Twin Prediction and What-if Simulation',
      subtitle: 'Digital-state prediction and fidelity under stale or noisy synchronisation.',
      icon: Database,
      className: 'left-[455px] top-[380px] w-[330px]',
      formula: 'Twin error = |predicted state - actual state| / max(|actual state|, e)\nTwin fidelity = max(0, 1 - twin error) x 100',
      liveValues: [
        ['NDT-only fidelity', `${round(getSummary(result.summaries, 'ndtOnly').twinFidelity, 1)}%`],
        ['FNDT fidelity', `${round(fedndt.twinFidelity, 1)}%`],
        ['FNDT twin error', round(fedndt.twinError, 3)],
        ['prediction MAE', round(fedndt.avgPredictionMae, 2)],
      ],
      impact: 'NDT adds prediction and what-if value, but fidelity degrades with mobility, congestion, and stale synchronisation.',
      accent: 'cyan',
      extra: (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[580px] text-left text-xs">
            <thead className="border-b border-white/10 text-slate-400">
              <tr>
                <th className="py-2 pr-3">Node</th>
                <th className="py-2 pr-3">Demand</th>
                <th className="py-2 pr-3">Predicted</th>
                <th className="py-2 pr-3">Reliability</th>
                <th className="py-2 pr-3">Quality</th>
              </tr>
            </thead>
            <tbody>
              {latestNodes.map((node) => (
                <tr key={node.nodeId} className="border-b border-white/5">
                  <td className="py-2 pr-3 font-semibold text-white">{node.nodeId}</td>
                  <td className="py-2 pr-3">{round(node.demand, 2)}</td>
                  <td className="py-2 pr-3">{round(node.predictedDemand, 2)}</td>
                  <td className="py-2 pr-3">{round(node.reliability, 3)}</td>
                  <td className="py-2 pr-3">{round(node.contributionQuality, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    },
    {
      id: 'incentive',
      code: 'L05',
      title: 'Incentive and Governance Engine',
      subtitle: 'Contribution quality, resource cost, participation, and reward variance.',
      icon: BrainCircuit,
      className: 'left-[70px] top-[580px] w-[250px]',
      formula: 'R_i = alpha Q_i - beta C_i + gamma P_i\nJ(x)=(sum_i x_i)^2/(n sum_i x_i^2)',
      liveValues: [
        ['alpha', controls.alpha],
        ['beta', controls.beta],
        ['gamma', controls.gamma],
        ['reward variance', round(fedndt.rewardVariance, 3)],
      ],
      impact: 'Good incentive weights improve participation and contribution quality, but manipulation and low-quality participants can still hurt results.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="α contribution quality" value={controls.alpha} min={0} max={1} step={0.01} onChange={(v) => updateControl('alpha', v)} />
          <SliderControl label="β resource cost" value={controls.beta} min={0} max={1} step={0.01} onChange={(v) => updateControl('beta', v)} />
          <SliderControl label="γ participation" value={controls.gamma} min={0} max={1} step={0.01} onChange={(v) => updateControl('gamma', v)} />
          <SliderControl label="Manipulation scenario" value={controls.incentiveManipulationRate} min={0} max={0.6} step={0.01} onChange={(v) => updateControl('incentiveManipulationRate', v)} />
          <ToggleControl label="Enable incentive scoring" checked={controls.incentiveEnabled} onChange={(v) => updateControl('incentiveEnabled', v)} />
        </div>
      ),
    },
    {
      id: 'action',
      code: 'L06',
      title: 'RAN + Edge Resource Action Engine',
      subtitle: 'QoS transformation through allocation, capacity, queueing, and latency.',
      icon: Network,
      className: 'left-[650px] top-[580px] w-[250px]',
      formula: 'rho_j=lambda_j/mu_j\nD=D_base+D_radio+D_queue+D_backhaul',
      liveValues: [
        ['radio noise', controls.radioNoiseLevel],
        ['queue scale', controls.queueScaleMs],
        ['SLA threshold', `${controls.slaThresholdMs} ms`],
        ['FNDT p95', `${result.architectureValues.fedndtP95} ms`],
      ],
      impact: 'Transforms allocation decisions into latency, packet loss, throughput, SLA violation, and energy proxies.',
      controls: (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliderControl label="Radio noise" value={controls.radioNoiseLevel} min={0.5} max={8} step={0.1} onChange={(v) => updateControl('radioNoiseLevel', v)} />
          <SliderControl label="Queue delay scale" value={controls.queueScaleMs} min={40} max={240} onChange={(v) => updateControl('queueScaleMs', v)} />
          <SliderControl label="Service calibration" value={controls.serviceCalibration} min={0.8} max={3.2} step={0.1} onChange={(v) => updateControl('serviceCalibration', v)} />
          <SliderControl label="SLA threshold" value={controls.slaThresholdMs} min={30} max={200} suffix=" ms" onChange={(v) => updateControl('slaThresholdMs', v)} />
        </div>
      ),
    },
    {
      id: 'baseline',
      code: 'L07',
      title: 'Baseline Comparator',
      subtitle: 'Heuristic baselines, architectural baselines, ablation, and proposed method.',
      icon: ShieldAlert,
      className: 'left-[360px] top-[580px] w-[250px]',
      formula: 'Static and Greedy are heuristic baselines.\nCentralised, FL-only, NDT-only, and FNDT without incentive are research-aligned architectural baselines.',
      liveValues: [
        ['methods', strategyOrder.length],
        ['centralised privacy proxy', result.architectureValues.centralizedPrivacy],
        ['FNDT overhead reduction', result.architectureValues.overheadReduction],
        ['validation', result.architectureValues.validation],
      ],
      impact: 'Separates traditional heuristics from the main research baselines used for architectural comparison.',
      accent: 'cyan',
    },
    {
      id: 'evaluation',
      code: 'L08',
      title: 'QoS, Fairness, and Claim-Safe Evaluation',
      subtitle: 'Direction-aware improvement, claim labels, and proxy metric caution.',
      icon: Gauge,
      className: 'left-[940px] top-[580px] w-[250px]',
      formula: 'Lower-is-better: ((baseline - proposed)/|baseline|) x 100\nHigher-is-better: ((proposed - baseline)/|baseline|) x 100',
      liveValues: [
        ['FNDT avg', `${round(fedndt.avgLatencyMs, 1)} ms`],
        ['Greedy avg', `${round(greedy.avgLatencyMs, 1)} ms`],
        ['Centralised avg', `${round(centralized.avgLatencyMs, 1)} ms`],
        ['Jain fairness', round(fedndt.jainFairness, 3)],
      ],
      impact: 'Uses strong, modest, neutral, and regression labels after metric-direction correction.',
      accent: 'emerald',
    },
  ]

  const activeLayer = layers.find((layer) => layer.id === activeLayerId) ?? layers[0]
  const ActiveIcon = activeLayer.icon

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="border-b border-cyan-400/10 bg-slate-950 px-6 py-5">
        <div className="mx-auto w-full max-w-[1920px]">
          <p className="mb-2 inline-flex rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1 text-xs font-medium text-cyan-200">
            Deterministic proof-of-concept simulator
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Federated Network Digital Twin RRM Simulator
          </h1>
          <p className="mt-3 max-w-5xl text-sm leading-6 text-slate-400 md:text-base">
            Claim-safe comparison of heuristic baselines, architectural baselines, ablations, and the proposed FNDT-Incentive method for edge and radio resource management.
          </p>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1920px] gap-4 px-6 py-5 md:grid-cols-4">
        {[
          [`${formatStrategy(primaryFocusedStrategy)} Average Latency`, `${round(focusedSummary.avgLatencyMs, 1)} ms`, 'lower is better'],
          [`${formatStrategy(primaryFocusedStrategy)} Twin Fidelity`, `${round(focusedSummary.twinFidelity, 1)}%`, 'NDT proxy'],
          [`${formatStrategy(primaryFocusedStrategy)} FL Loss`, round(focusedSummary.flLoss, 3), 'convergence proxy'],
          [`${formatStrategy(primaryFocusedStrategy)} Jain Fairness`, round(focusedSummary.jainFairness, 3), 'higher is fairer'],
        ].map(([label, value, note]) => (
          <div key={label} className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs font-medium text-slate-400">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
            <p className="mt-1 text-[11px] text-slate-500">{note}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto grid w-full max-w-[1760px] gap-5 px-6 pb-8 2xl:grid-cols-[minmax(0,1fr)_430px]">
        <div className="min-w-0">
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-white md:text-3xl">Interactive FedNDT framework canvas</h2>
            <p className="mt-2 max-w-5xl text-sm leading-6 text-slate-400">
              The original framework diagram is preserved. New research controls and metrics open in the layer inspector.
            </p>
            <FilterHint selectedStrategies={selectedStrategies} clearSelection={clearSelection} />
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
              <p className="text-sm text-slate-400">Average latency trajectory for all seven methods.</p>
              <StrategyLegend strategies={lineStrategies} {...strategyInteraction} />
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.latencyTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="step" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" tickFormatter={(value) => `${value} ms`} />
                    <Tooltip content={<MetricTooltip metric="avgLatencyMs" strategy={hoveredStrategy ?? undefined} summaries={result.summaries} />} />
                    {lineStrategies.map((strategy) => (
                      <Line
                        key={strategy}
                        type="monotone"
                        dataKey={strategy}
                        name={formatStrategy(strategy)}
                        stroke={strategyCapabilities.find((item) => item.strategy === strategy)?.color}
                        strokeWidth={getStrategyOpacity(strategy) === 1 ? (strategy === 'fedndt' ? 4 : 3) : 1.5}
                        strokeOpacity={getStrategyOpacity(strategy)}
                        dot={false}
                        activeDot={{ r: 5, style: clickableChartStyle, onClick: (event) => handleStrategyClick(strategy, event) }}
                        style={clickableChartStyle}
                        onClick={(event) => handleStrategyClick(strategy, event)}
                        onMouseEnter={() => setHoveredStrategy(strategy)}
                        onMouseLeave={() => setHoveredStrategy(null)}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-2xl font-semibold text-white">Strategy comparison</h2>
                  <p className="text-sm text-slate-400">
                    {activeMetric.label}. Unit: {activeMetric.unit}. Direction: {metricDirectionText(selectedMetric)}.
                  </p>
                </div>
                <label className="min-w-[220px]">
                  <span className="block text-xs font-semibold uppercase tracking-wide text-slate-400">Metric</span>
                  <select
                    value={selectedMetric}
                    onChange={(event) => setSelectedMetric(event.target.value as MetricKey)}
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
              <StrategyLegend strategies={strategyOrder} {...strategyInteraction} />
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartSummaries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="strategy" stroke="#94a3b8" interval={0} angle={-20} textAnchor="end" height={80} />
                    <YAxis stroke="#94a3b8" tickFormatter={(value) => String(round(value as number, activeMetric.digits ?? 2))} />
                    <Tooltip content={<MetricTooltip metric={selectedMetric} summaries={result.summaries} />} />
                    <Bar dataKey="value" name={activeMetric.label} radius={[8, 8, 0, 0]}>
                      {chartSummaries.map((entry) => (
                        <Cell
                          key={entry.strategyId}
                          fill={strategyColor(entry.strategyId)}
                          fillOpacity={getStrategyOpacity(entry.strategyId)}
                          stroke={getStrategyOpacity(entry.strategyId) === 1 && selectedStrategies.includes(entry.strategyId) ? '#e0f2fe' : 'transparent'}
                          strokeWidth={2}
                          style={clickableChartStyle}
                          onClick={(event) => handleStrategyClick(entry.strategyId, event)}
                          onMouseEnter={() => setHoveredStrategy(entry.strategyId)}
                          onMouseLeave={() => setHoveredStrategy(null)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-2xl font-semibold text-white">Communication overhead</h2>
              <p className="text-sm text-slate-400">Proxy split into raw telemetry, model updates, twin sync, and governance metadata.</p>
              <StrategyLegend strategies={strategyOrder} {...strategyInteraction} />
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.overheadBreakdown}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="strategy" stroke="#94a3b8" interval={0} angle={-20} textAnchor="end" height={80} />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip content={<MetricTooltip metric="communicationOverhead" summaries={result.summaries} />} />
                    <Legend />
                    {[
                      ['rawTelemetryOverhead', 'Raw telemetry', '#f59e0b'],
                      ['modelUpdateOverhead', 'Model updates', '#a78bfa'],
                      ['twinSyncOverhead', 'Twin sync', '#14b8a6'],
                      ['governanceOverhead', 'Governance metadata', '#22c55e'],
                    ].map(([dataKey, name, fill]) => (
                      <Bar key={dataKey} dataKey={dataKey} name={name} stackId="a" fill={fill}>
                        {result.overheadBreakdown.map((entry) => {
                          const strategyId = entry.strategyId as Strategy
                          return (
                            <Cell
                              key={`${dataKey}-${strategyId}`}
                              fillOpacity={getStrategyOpacity(strategyId)}
                              style={clickableChartStyle}
                              onClick={(event) => handleStrategyClick(strategyId, event)}
                              onMouseEnter={() => setHoveredStrategy(strategyId)}
                              onMouseLeave={() => setHoveredStrategy(null)}
                            />
                          )
                        })}
                      </Bar>
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-2xl font-semibold text-white">Privacy exposure proxy</h2>
              <p className="text-sm text-slate-400">Proxy score from raw-data centralisation and synchronization level. This is not a privacy proof.</p>
              <StrategyLegend strategies={strategyOrder} {...strategyInteraction} />
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.summaries.map((summary) => ({ strategy: formatStrategy(summary.strategy), value: round(summary.privacyExposure, 2), strategyId: summary.strategy }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="strategy" stroke="#94a3b8" interval={0} angle={-20} textAnchor="end" height={80} />
                    <YAxis stroke="#94a3b8" domain={[0, 1]} />
                    <Tooltip content={<MetricTooltip metric="privacyExposure" summaries={result.summaries} />} />
                    <Bar dataKey="value" name="Privacy exposure proxy" radius={[8, 8, 0, 0]}>
                      {result.summaries.map((entry) => (
                        <Cell
                          key={entry.strategy}
                          fill={strategyColor(entry.strategy)}
                          fillOpacity={getStrategyOpacity(entry.strategy)}
                          stroke={getStrategyOpacity(entry.strategy) === 1 && selectedStrategies.includes(entry.strategy) ? '#e0f2fe' : 'transparent'}
                          strokeWidth={2}
                          style={clickableChartStyle}
                          onClick={(event) => handleStrategyClick(entry.strategy, event)}
                          onMouseEnter={() => setHoveredStrategy(entry.strategy)}
                          onMouseLeave={() => setHoveredStrategy(null)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-2xl font-semibold text-white">Twin fidelity</h2>
              <p className="text-sm text-slate-400">Shown for NDT-based methods only.</p>
              <StrategyLegend strategies={ndtStrategies} {...strategyInteraction} />
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.twinFidelityTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="step" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" tickFormatter={(value) => `${value}%`} />
                    <Tooltip content={<MetricTooltip metric="twinFidelity" strategy={hoveredStrategy ?? undefined} summaries={result.summaries} />} />
                    {ndtStrategies.map((strategy) => (
                      <Line
                        key={strategy}
                        type="monotone"
                        dataKey={strategy}
                        name={formatStrategy(strategy)}
                        stroke={strategyColor(strategy)}
                        strokeWidth={getStrategyOpacity(strategy) === 1 ? 3 : 1.5}
                        strokeOpacity={getStrategyOpacity(strategy)}
                        dot={false}
                        activeDot={{ r: 5, style: clickableChartStyle, onClick: (event) => handleStrategyClick(strategy, event) }}
                        style={clickableChartStyle}
                        onClick={(event) => handleStrategyClick(strategy, event)}
                        onMouseEnter={() => setHoveredStrategy(strategy)}
                        onMouseLeave={() => setHoveredStrategy(null)}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-2xl font-semibold text-white">FL convergence</h2>
              <p className="text-sm text-slate-400">FL loss over rounds for FL-based methods.</p>
              <StrategyLegend strategies={flStrategies} {...strategyInteraction} />
              <div className="mt-6 h-80 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.flConvergence}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="round" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip content={<MetricTooltip metric="flLoss" strategy={hoveredStrategy ?? undefined} summaries={result.summaries} />} />
                    {flStrategies.map((strategy) => (
                      <Line
                        key={strategy}
                        type="monotone"
                        dataKey="flLoss"
                        data={result.flConvergence.filter((row) => row.strategy === strategy)}
                        name={formatStrategy(strategy)}
                        stroke={strategyColor(strategy)}
                        strokeWidth={getStrategyOpacity(strategy) === 1 ? 3 : 1.5}
                        strokeOpacity={getStrategyOpacity(strategy)}
                        dot={false}
                        activeDot={{ r: 5, style: clickableChartStyle, onClick: (event) => handleStrategyClick(strategy, event) }}
                        style={clickableChartStyle}
                        onClick={(event) => handleStrategyClick(strategy, event)}
                        onMouseEnter={() => setHoveredStrategy(strategy)}
                        onMouseLeave={() => setHoveredStrategy(null)}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <h2 className="text-2xl font-semibold text-white">Incentive and fairness</h2>
              <p className="text-sm text-slate-400">Jain fairness, participation, contribution quality, and reward distribution proxies.</p>
              <div className="mt-5 grid gap-3 md:grid-cols-4">
                <MetricPill label={`${formatStrategy(incentiveStrategy)} Jain fairness`} value={round(incentiveSummary.jainFairness, 3)} />
                <MetricPill label="Participation" value={`${round(incentiveSummary.participationRate, 1)}%`} />
                <MetricPill label="Contribution quality" value={round(incentiveSummary.contributionQuality, 2)} />
                <MetricPill label="Reward variance" value={round(incentiveSummary.rewardVariance, 3)} />
              </div>
              <StrategyLegend strategies={['fndtNoIncentive', 'fedndt']} {...strategyInteraction} />
              <div className="mt-6 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.rewardDistribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                    <XAxis dataKey="node" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip content={<MetricTooltip metric="rewardVariance" />} />
                    <Legend />
                    <Bar dataKey="reward" name="Reward score" radius={[8, 8, 0, 0]}>
                      {result.rewardDistribution.map((entry, index) => {
                        const strategyId = entry.strategyId as Strategy
                        return (
                          <Cell
                            key={`${strategyId}-${String(entry.node)}-${index}`}
                            fill={strategyColor(strategyId)}
                            fillOpacity={getStrategyOpacity(strategyId)}
                            style={clickableChartStyle}
                            onClick={(event) => handleStrategyClick(strategyId, event)}
                            onMouseEnter={() => setHoveredStrategy(strategyId)}
                            onMouseLeave={() => setHoveredStrategy(null)}
                          />
                        )
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-2xl font-semibold text-white">Claim-safe summary</h2>
                  <p className="text-sm text-slate-400">
                    Selected comparison: {formatStrategy(selectedBaseline)} vs FNDT-Incentive. Direction-correct improvement for FNDT-Incentive.
                  </p>
                </div>
                <label className="min-w-[220px]">
                  <span className="block text-xs font-semibold uppercase tracking-wide text-slate-400">Baseline</span>
                  <select
                    value={selectedBaseline}
                    onChange={(event) => setClaimBaseline(event.target.value as Strategy)}
                    className="mt-2 w-full rounded-xl border border-cyan-300/20 bg-slate-900 px-3 py-2 text-sm font-semibold text-white outline-none focus:border-cyan-300"
                  >
                    {strategyOrder.filter((strategy) => strategy !== 'fedndt').map((strategy) => (
                      <option key={strategy} value={strategy}>
                        {formatStrategy(strategy)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-5 space-y-3">
                {claims.map((claim) => (
                  <div key={claim.metric} className="rounded-xl border border-white/10 bg-slate-950/70 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold text-white">{claim.label}</p>
                        <p className="mt-1 text-[11px] text-slate-500">
                          FNDT {formatMetricValue(claim.proposedValue, claim.metric)} vs {formatStrategy(selectedBaseline)} {formatMetricValue(claim.baselineValue, claim.metric)}
                        </p>
                      </div>
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold ${strengthClass(claim.strength)}`}>
                        {claim.strength.replace('_', ' ')} · {round(claim.improvement, 1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
            <h2 className="text-2xl font-semibold text-white">Baseline comparison table</h2>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[1180px] text-left text-xs">
                <thead className="border-b border-white/10 text-slate-400">
                  <tr>
                    <th className="py-2 pr-3">Strategy</th>
                    <th className="py-2 pr-3">Role</th>
                    <th className="py-2 pr-3">FL</th>
                    <th className="py-2 pr-3">NDT</th>
                    <th className="py-2 pr-3">Incentive</th>
                    <th className="py-2 pr-3">Raw Data Sharing</th>
                    <th className="py-2 pr-3">Overhead</th>
                    <th className="py-2 pr-3">Privacy Exposure</th>
                    <th className="py-2 pr-3">Predictive Simulation</th>
                    <th className="py-2 pr-3">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {strategyCapabilities.map((capability) => {
                    const summary = getSummary(result.summaries, capability.strategy)
                    return (
                      <tr
                        key={capability.strategy}
                        tabIndex={0}
                        onClick={(event) => handleStrategyClick(capability.strategy, event)}
                        onMouseEnter={() => setHoveredStrategy(capability.strategy)}
                        onMouseLeave={() => setHoveredStrategy(null)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            handleStrategyClick(capability.strategy, event)
                          }
                        }}
                        className={`cursor-pointer border-b border-white/5 text-slate-300 transition ${
                          selectedStrategies.includes(capability.strategy)
                            ? 'bg-cyan-300/10 text-white outline outline-1 outline-cyan-200/40'
                            : 'hover:bg-white/[0.04]'
                        }`}
                        style={{ opacity: getStrategyOpacity(capability.strategy) }}
                        aria-label={`Select ${capability.label}`}
                      >
                        <td className="py-2 pr-3 font-semibold text-white">{capability.label}</td>
                        <td className="py-2 pr-3">{strategyRole(capability.strategy)}</td>
                        <td className="py-2 pr-3">{capability.fl ? 'Yes' : 'No'}</td>
                        <td className="py-2 pr-3">{capability.ndt ? 'Yes' : 'No'}</td>
                        <td className="py-2 pr-3">{capability.incentive ? 'Yes' : 'No'}</td>
                        <td className="py-2 pr-3">{capability.rawDataSharing}</td>
                        <td className="py-2 pr-3">{round(summary.communicationOverhead, 2)} MB/round</td>
                        <td className="py-2 pr-3">{round(summary.privacyExposure, 2)} proxy</td>
                        <td className="py-2 pr-3">{capability.predictiveSimulation ? 'Yes' : 'No'}</td>
                        <td className="py-2 pr-3">{capability.researchRole}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-amber-300/20 bg-amber-300/[0.06] p-6">
            <h2 className="text-2xl font-semibold text-white">Limitations</h2>
            <p className="mt-3 text-sm leading-6 text-amber-100/80">
              This simulator is a deterministic proof-of-concept used to illustrate architectural behaviour under configurable conditions. It does not prove real-world network performance. Publication-strength validation requires Monte Carlo trials, multiple random seeds, calibrated channel models, NS-3 or equivalent validation, and comparison using mean ± standard deviation.
            </p>
          </div>
        </div>

        <aside className="2xl:sticky 2xl:top-5 2xl:self-start">
          <div className="max-h-[calc(100vh-2.5rem)] overflow-y-auto rounded-[2rem] border border-white/10 bg-white/[0.04] p-4 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-3">
                <ActiveIcon className="h-6 w-6 text-cyan-200" />
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-300">{activeLayer.code} Layer Inspector</p>
                <h2 className="mt-1 text-xl font-semibold text-white">{activeLayer.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">{activeLayer.subtitle}</p>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <DetailsSection title="Mathematical model" defaultOpen>
                <pre className="whitespace-pre-wrap rounded-2xl border border-white/10 bg-black/25 p-4 text-xs leading-6 text-slate-100">
                  {activeLayer.formula}
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
                <DetailsSection title={activeLayer.id === 'ndt' ? 'Latest twin state' : 'Layer details'} defaultOpen>
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
          <strong className="text-slate-200">Scope note:</strong> Results are illustrative simulation outputs with proxy metrics for privacy exposure, communication overhead, twin fidelity, FL convergence, and incentives. Treat the comparison as claim-safe architectural exploration, not empirical proof.
        </div>
      </section>
    </main>
  )
}

export default App
