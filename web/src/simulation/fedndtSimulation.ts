export type Strategy = 'static' | 'greedy' | 'fedndt'

export type SimulationControls = {
  numUsers: number
  numNodes: number
  totalResources: number
  timeSteps: number
  trafficIntensity: number
  peakMultiplier: number
  mobilityShiftProbability: number
  overloadedNode: number
  overloadMultiplier: number
  unreliableNode: number
  staleUpdateProbability: number
  reportingNoiseProbability: number
  greedyDelaySteps: number
  incentiveEnabled: boolean
  slaThresholdMs: number
  radioNoiseLevel: number
  alpha: number
  beta: number
  gamma: number
  delta: number
  eta: number
  queueScaleMs: number
  serviceCalibration: number
  radioDelayScale: number
}

export type NodeSnapshot = {
  step: number
  nodeId: number
  demand: number
  predictedDemand: number
  radioQualityDb: number
  sinrLinear: number
  capacityMbps: number
  reliability: number
  congestionRisk: number
  freshnessScore: number
  accuracyScore: number
  consistencyScore: number
  participationScore: number
}

export type StrategyStep = {
  step: number
  strategy: Strategy
  nodeId: number
  allocation: number
  demand: number
  predictedDemand: number
  reliability: number
  radioQualityDb: number
  sinrLinear: number
  capacityMbps: number
  queueRho: number
  queueDelayMs: number
  radioDelayMs: number
  backhaulDelayMs: number
  latencyMs: number
  latencyExcessMs: number
  throughput: number
  slaViolation: number
  severeSlaViolation: number
}

export type StrategySummary = {
  strategy: Strategy
  avgLatencyMs: number
  p95LatencyMs: number
  p99LatencyMs: number
  slaViolationRate: number
  severeSlaViolationRate: number
  avgLatencyExcessMs: number
  maxLatencyExcessMs: number
  avgThroughput: number
  resourceFairness: number
  throughputFairness: number
  avgReliability: number
  avgQueueRho: number
  avgCapacityMbps: number
  avgPredictionMae: number
  overheadReductionRatio: number
  utilityScore: number
}

export type SimulationResult = {
  controls: SimulationControls
  nodeSnapshots: NodeSnapshot[]
  steps: StrategyStep[]
  summaries: StrategySummary[]
  latencyTrend: Array<Record<string, number>>
  architectureValues: Record<string, string | number>
}

const EPSILON = 1e-9

export const defaultControls: SimulationControls = {
  numUsers: 75,
  numNodes: 3,
  totalResources: 120,
  timeSteps: 120,
  trafficIntensity: 1.0,
  peakMultiplier: 2.8,
  mobilityShiftProbability: 0.22,
  overloadedNode: 1,
  overloadMultiplier: 2.6,
  unreliableNode: 2,
  staleUpdateProbability: 0.25,
  reportingNoiseProbability: 0.35,
  greedyDelaySteps: 5,
  incentiveEnabled: true,
  slaThresholdMs: 50,
  radioNoiseLevel: 2.2,
  alpha: 0.30,
  beta: 0.25,
  gamma: 0.20,
  delta: 0.15,
  eta: 0.10,
  queueScaleMs: 120,
  serviceCalibration: 1.9,
  radioDelayScale: 4,
}

function seededRandom(seed: number) {
  let state = seed >>> 0
  return () => {
    state = (1664525 * state + 1013904223) >>> 0
    return state / 4294967296
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function mean(values: number[]) {
  if (!values.length) return 0
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function percentile(values: number[], p: number) {
  if (!values.length) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const rank = (sorted.length - 1) * (p / 100)
  const lower = Math.floor(rank)
  const upper = Math.ceil(rank)
  if (lower === upper) return sorted[lower]
  const weight = rank - lower
  return sorted[lower] + (sorted[upper] - sorted[lower]) * weight
}

function jainFairness(values: number[]) {
  const positive = values.map((value) => Math.max(0, value))
  const numerator = positive.reduce((sum, value) => sum + value, 0) ** 2
  const denominator = positive.length * positive.reduce((sum, value) => sum + value ** 2, 0)
  if (denominator <= EPSILON) return 0
  return numerator / denominator
}

function dbToLinear(db: number) {
  return 10 ** (db / 10)
}

function shannonCapacityMbps(bandwidthMhz: number, sinrLinear: number) {
  return Math.max(0, bandwidthMhz) * Math.log2(1 + Math.max(0, sinrLinear))
}

function normalizeWeights(controls: SimulationControls) {
  const raw = {
    alpha: Math.max(0, controls.alpha),
    beta: Math.max(0, controls.beta),
    gamma: Math.max(0, controls.gamma),
    delta: Math.max(0, controls.delta),
    eta: Math.max(0, controls.eta),
  }
  const total = raw.alpha + raw.beta + raw.gamma + raw.delta + raw.eta || 1
  return {
    alpha: raw.alpha / total,
    beta: raw.beta / total,
    gamma: raw.gamma / total,
    delta: raw.delta / total,
    eta: raw.eta / total,
  }
}

function normalizeVector(values: number[]) {
  const maxValue = Math.max(...values, EPSILON)
  return values.map((value) => value / maxValue)
}

function generateNodeSnapshots(controls: SimulationControls): NodeSnapshot[] {
  const random = seededRandom(42)
  const snapshots: NodeSnapshot[] = []
  const history: Record<number, number[]> = {}

  for (let nodeId = 0; nodeId < controls.numNodes; nodeId += 1) {
    history[nodeId] = []
  }

  for (let step = 0; step < controls.timeSteps; step += 1) {
    const peakWave = 1 + (controls.peakMultiplier - 1) * Math.max(0, Math.sin((Math.PI * step) / controls.timeSteps))
    const overloadActive = step > controls.timeSteps * 0.35 && step < controls.timeSteps * 0.72

    for (let nodeId = 0; nodeId < controls.numNodes; nodeId += 1) {
      const baseShare = controls.numUsers / controls.numNodes
      const nodeBias = 0.85 + nodeId * 0.12
      const noise = 0.85 + random() * 0.3
      const mobilityBoost = random() < controls.mobilityShiftProbability ? 1.2 + random() * 0.6 : 1
      const overloadBoost = overloadActive && nodeId === controls.overloadedNode ? controls.overloadMultiplier : 1

      let demand = baseShare * controls.trafficIntensity * peakWave * nodeBias * noise * mobilityBoost * overloadBoost

      const isUnreliable = nodeId === controls.unreliableNode
      const stale = isUnreliable && random() < controls.staleUpdateProbability
      const noisy = isUnreliable && random() < controls.reportingNoiseProbability

      const previousDemand = history[nodeId].length ? history[nodeId][history[nodeId].length - 1] : demand
      if (stale) demand = previousDemand
      if (noisy) demand *= 0.8 + random() * 0.5

      const previous = history[nodeId]
      const predictedDemand = previous.length
        ? 0.58 * previousDemand + 0.42 * mean(previous.slice(-6))
        : demand

      const predictionError = Math.abs(demand - predictedDemand)
      const accuracyScore = 1 - Math.min(predictionError / Math.max(demand, EPSILON), 1)
      const freshnessScore = stale ? Math.exp(-2.0) : 1
      const consistencyScore = noisy ? 0.62 : 0.92
      const participationScore = stale ? 0.72 : 1

      const reliability = controls.incentiveEnabled
        ? 0.25 * freshnessScore + 0.35 * accuracyScore + 0.25 * consistencyScore + 0.15 * participationScore
        : 1

      const baseQuality = 18 - controls.radioNoiseLevel + nodeId * 0.5
      const qualityNoise = (random() - 0.5) * controls.radioNoiseLevel * 2
      const radioQualityDb = clamp(baseQuality + qualityNoise - (overloadBoost > 1 ? 2.5 : 0), -5, 35)
      const sinrLinear = dbToLinear(radioQualityDb)
      const capacityMbps = shannonCapacityMbps(10, sinrLinear)
      const congestionRisk = clamp(demand / Math.max(baseShare * controls.peakMultiplier, EPSILON), 0, 2)

      snapshots.push({
        step,
        nodeId,
        demand,
        predictedDemand,
        radioQualityDb,
        sinrLinear,
        capacityMbps,
        reliability: clamp(reliability, 0, 1),
        congestionRisk,
        freshnessScore,
        accuracyScore,
        consistencyScore,
        participationScore,
      })

      history[nodeId].push(demand)
    }
  }

  return snapshots
}

function allocateForStep(stepNodes: NodeSnapshot[], strategy: Strategy, controls: SimulationControls): number[] {
  if (strategy === 'static') {
    return stepNodes.map(() => controls.totalResources / controls.numNodes)
  }

  if (strategy === 'greedy') {
    const delayedStep = Math.max(0, stepNodes[0].step - controls.greedyDelaySteps)
    const sameNodes = stepNodes.map((node) => ({ ...node, demand: node.step === delayedStep ? node.demand : node.demand }))
    const scores = sameNodes.map((node) => Math.max(node.demand, EPSILON))
    const totalScore = scores.reduce((sum, score) => sum + score, 0)
    return scores.map((score) => (controls.totalResources * score) / totalScore)
  }

  const weights = normalizeWeights(controls)
  const predicted = normalizeVector(stepNodes.map((node) => node.predictedDemand))
  const current = normalizeVector(stepNodes.map((node) => node.demand))
  const congestion = normalizeVector(stepNodes.map((node) => node.congestionRisk))
  const reliability = stepNodes.map((node) => node.reliability)
  const inversePrevious = stepNodes.map((node) => 1 / Math.max(node.demand, EPSILON))
  const fairness = normalizeVector(inversePrevious)

  const scores = stepNodes.map((_node, index) =>
    weights.alpha * predicted[index] +
    weights.beta * current[index] +
    weights.gamma * congestion[index] +
    weights.delta * reliability[index] +
    weights.eta * fairness[index],
  )

  const totalScore = scores.reduce((sum, score) => sum + score, 0) || 1
  return scores.map((score) => (controls.totalResources * score) / totalScore)
}

function evaluateStrategyStep(
  node: NodeSnapshot,
  allocation: number,
  strategy: Strategy,
  controls: SimulationControls,
): StrategyStep {
  const bandwidthMhz = allocation * 0.25
  const capacityMbps = shannonCapacityMbps(bandwidthMhz, node.sinrLinear)
  const serviceRate = allocation * controls.serviceCalibration * clamp(capacityMbps / Math.max(allocation, EPSILON), 0.3, 2.2)
  const queueRho = node.demand / Math.max(serviceRate, EPSILON)
  const remainingCapacity = Math.max(serviceRate - node.demand, 1e-6)
  const queueDelayMs = Math.min(controls.queueScaleMs / remainingCapacity, 900)
  const radioDelayMs = Math.min(controls.radioDelayScale * (node.demand / Math.max(capacityMbps, EPSILON)), 250)
  const backhaulDelayMs = 3 + 12 * node.congestionRisk
  const latencyMs = Math.min(10 + queueDelayMs + radioDelayMs + backhaulDelayMs, 10000)
  const latencyExcessMs = Math.max(0, latencyMs - controls.slaThresholdMs)
  const overloadPenalty = Math.min(Math.max(queueRho - 1, 0), 1)
  const throughput = Math.max(0, serviceRate * (1 - 0.5 * overloadPenalty))

  return {
    step: node.step,
    strategy,
    nodeId: node.nodeId,
    allocation,
    demand: node.demand,
    predictedDemand: node.predictedDemand,
    reliability: node.reliability,
    radioQualityDb: node.radioQualityDb,
    sinrLinear: node.sinrLinear,
    capacityMbps,
    queueRho,
    queueDelayMs,
    radioDelayMs,
    backhaulDelayMs,
    latencyMs,
    latencyExcessMs,
    throughput,
    slaViolation: latencyMs > controls.slaThresholdMs ? 1 : 0,
    severeSlaViolation: latencyMs > controls.slaThresholdMs * 2 ? 1 : 0,
  }
}

function summarizeStrategy(strategy: Strategy, rows: StrategyStep[], controls: SimulationControls): StrategySummary {
  const latencies = rows.map((row) => row.latencyMs)
  const excess = rows.map((row) => row.latencyExcessMs)
  const throughput = rows.map((row) => row.throughput)
  const reliability = rows.map((row) => row.reliability)
  const queueRhos = rows.map((row) => row.queueRho)
  const capacities = rows.map((row) => row.capacityMbps)
  const predictionErrors = rows.map((row) => Math.abs(row.demand - row.predictedDemand))

  const perStepAllocFairness: number[] = []
  const perStepThroughputFairness: number[] = []

  for (let step = 0; step < controls.timeSteps; step += 1) {
    const stepRows = rows.filter((row) => row.step === step)
    perStepAllocFairness.push(jainFairness(stepRows.map((row) => row.allocation)))
    perStepThroughputFairness.push(jainFairness(stepRows.map((row) => row.throughput)))
  }

  const communicationOverhead =
    strategy === 'fedndt'
      ? controls.numNodes * 24 * controls.timeSteps
      : strategy === 'greedy'
        ? controls.numNodes * 56 * controls.timeSteps
        : 0

  const greedyOverhead = controls.numNodes * 56 * controls.timeSteps
  const overheadReductionRatio = strategy === 'fedndt' ? (greedyOverhead - communicationOverhead) / greedyOverhead : 0

  const utilityScore =
    throughput.reduce((sum, value) => sum + Math.log(value + EPSILON), 0) -
    mean(excess) -
    mean(rows.map((row) => row.slaViolation)) -
    communicationOverhead * 1e-6

  return {
    strategy,
    avgLatencyMs: mean(latencies),
    p95LatencyMs: percentile(latencies, 95),
    p99LatencyMs: percentile(latencies, 99),
    slaViolationRate: mean(rows.map((row) => row.slaViolation)),
    severeSlaViolationRate: mean(rows.map((row) => row.severeSlaViolation)),
    avgLatencyExcessMs: mean(excess),
    maxLatencyExcessMs: Math.max(...excess),
    avgThroughput: mean(throughput),
    resourceFairness: mean(perStepAllocFairness),
    throughputFairness: mean(perStepThroughputFairness),
    avgReliability: mean(reliability),
    avgQueueRho: mean(queueRhos),
    avgCapacityMbps: mean(capacities),
    avgPredictionMae: mean(predictionErrors),
    overheadReductionRatio,
    utilityScore,
  }
}

export function runSimulation(controls: SimulationControls): SimulationResult {
  const normalizedControls = {
    ...controls,
    numNodes: Math.max(2, Math.round(controls.numNodes)),
    numUsers: Math.max(10, Math.round(controls.numUsers)),
    timeSteps: Math.max(20, Math.round(controls.timeSteps)),
    overloadedNode: clamp(Math.round(controls.overloadedNode), 0, Math.max(0, Math.round(controls.numNodes) - 1)),
    unreliableNode: clamp(Math.round(controls.unreliableNode), 0, Math.max(0, Math.round(controls.numNodes) - 1)),
  }

  const nodeSnapshots = generateNodeSnapshots(normalizedControls)
  const allSteps: StrategyStep[] = []
  const strategies: Strategy[] = ['static', 'greedy', 'fedndt']

  for (let step = 0; step < normalizedControls.timeSteps; step += 1) {
    const stepNodes = nodeSnapshots.filter((node) => node.step === step)
    for (const strategy of strategies) {
      const allocations = allocateForStep(stepNodes, strategy, normalizedControls)
      stepNodes.forEach((node, index) => {
        allSteps.push(evaluateStrategyStep(node, allocations[index], strategy, normalizedControls))
      })
    }
  }

  const summaries = strategies.map((strategy) =>
    summarizeStrategy(
      strategy,
      allSteps.filter((row) => row.strategy === strategy),
      normalizedControls,
    ),
  )

  const latencyTrend = Array.from({ length: normalizedControls.timeSteps }, (_, step) => {
    const record: Record<string, number> = { step }
    for (const strategy of strategies) {
      record[strategy] = mean(
        allSteps.filter((row) => row.step === step && row.strategy === strategy).map((row) => row.latencyMs),
      )
    }
    return record
  })

  const fedndt = summaries.find((summary) => summary.strategy === 'fedndt')!
  const architectureValues = {
    users: normalizedControls.numUsers,
    nodes: normalizedControls.numNodes,
    totalResources: normalizedControls.totalResources,
    avgDemand: mean(nodeSnapshots.map((node) => node.demand)).toFixed(2),
    avgReliability: mean(nodeSnapshots.map((node) => node.reliability)).toFixed(3),
    avgCapacityMbps: fedndt.avgCapacityMbps.toFixed(2),
    fedndtP95: fedndt.p95LatencyMs.toFixed(1),
    fedndtFairness: fedndt.throughputFairness.toFixed(3),
    overheadReduction: `${(fedndt.overheadReductionRatio * 100).toFixed(1)}%`,
  }

  return {
    controls: normalizedControls,
    nodeSnapshots,
    steps: allSteps,
    summaries,
    latencyTrend,
    architectureValues,
  }
}

export function formatStrategy(strategy: Strategy) {
  if (strategy === 'fedndt') return 'FedNDT-Incentive'
  if (strategy === 'greedy') return 'Greedy'
  return 'Static'
}

export function round(value: number, digits = 2) {
  return Number(value.toFixed(digits))
}
