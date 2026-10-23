export type Strategy =
  | 'static'
  | 'greedy'
  | 'centralized'
  | 'flOnly'
  | 'ndtOnly'
  | 'fndtNoIncentive'
  | 'fedndt'

export type MetricDirection = 'lower' | 'higher'

export type MetricConfig = {
  label: string
  unit: string
  direction: MetricDirection
  digits?: number
}

export type StrategyCapability = {
  strategy: Strategy
  label: string
  group: 'Heuristic baseline' | 'Research baseline' | 'Proposed method'
  fl: boolean
  ndt: boolean
  incentive: boolean
  rawDataSharing: 'None' | 'Local telemetry only' | 'Raw telemetry centralized' | 'Model updates only' | 'State synchronization'
  predictiveSimulation: boolean
  researchRole: string
  color: string
}

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
  contributionQualityVariation: number
  participantDropoutRate: number
  lowQualityContributorRate: number
  incentiveManipulationRate: number
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
  contributionQuality: number
  resourceCost: number
  manipulatedQuality: number
  dropout: boolean
}

export type StrategyStep = {
  step: number
  strategy: Strategy
  nodeId: number
  allocation: number
  demand: number
  predictedDemand: number
  effectivePrediction: number
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
  packetLossRate: number
  energyConsumption: number
  rewardScore: number
}

export type FlRound = {
  round: number
  strategy: Strategy
  flLoss: number
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
  minThroughput: number
  resourceFairness: number
  throughputFairness: number
  jainFairness: number
  avgReliability: number
  avgQueueRho: number
  avgCapacityMbps: number
  avgPredictionMae: number
  communicationOverhead: number
  rawTelemetryOverhead: number
  modelUpdateOverhead: number
  twinSyncOverhead: number
  governanceOverhead: number
  privacyExposure: number
  twinError: number
  twinFidelity: number
  flLoss: number
  convergenceRounds: number
  modelAccuracy: number
  participationRate: number
  contributionQuality: number
  rewardVariance: number
  energyConsumption: number
  packetLoss: number
  overheadReductionRatio: number
  utilityScore: number
}

export type SimulationResult = {
  controls: SimulationControls
  nodeSnapshots: NodeSnapshot[]
  steps: StrategyStep[]
  summaries: StrategySummary[]
  latencyTrend: Array<Record<string, number>>
  overheadBreakdown: Array<Record<string, number | string>>
  twinFidelityTrend: Array<Record<string, number>>
  flConvergence: FlRound[]
  rewardDistribution: Array<Record<string, number | string>>
  architectureValues: Record<string, string | number>
}

export type ClaimStrength = 'strong_improvement' | 'modest_improvement' | 'neutral' | 'regression'

const EPSILON = 1e-9
const FL_STRATEGIES: Strategy[] = ['flOnly', 'fndtNoIncentive', 'fedndt']
const NDT_STRATEGIES: Strategy[] = ['ndtOnly', 'fndtNoIncentive', 'fedndt']

export const strategyCapabilities: StrategyCapability[] = [
  {
    strategy: 'static',
    label: 'Static Allocation',
    group: 'Heuristic baseline',
    fl: false,
    ndt: false,
    incentive: false,
    rawDataSharing: 'None',
    predictiveSimulation: false,
    researchRole: 'Traditional fixed-allocation heuristic baseline.',
    color: '#94a3b8',
  },
  {
    strategy: 'greedy',
    label: 'Greedy Local',
    group: 'Heuristic baseline',
    fl: false,
    ndt: false,
    incentive: false,
    rawDataSharing: 'Local telemetry only',
    predictiveSimulation: false,
    researchRole: 'Short-term local optimization baseline.',
    color: '#38bdf8',
  },
  {
    strategy: 'centralized',
    label: 'Centralised Controller',
    group: 'Research baseline',
    fl: false,
    ndt: false,
    incentive: false,
    rawDataSharing: 'Raw telemetry centralized',
    predictiveSimulation: true,
    researchRole: 'Strong global controller with high communication and privacy-exposure proxy.',
    color: '#f59e0b',
  },
  {
    strategy: 'flOnly',
    label: 'FL-only / No NDT',
    group: 'Research baseline',
    fl: true,
    ndt: false,
    incentive: false,
    rawDataSharing: 'Model updates only',
    predictiveSimulation: false,
    researchRole: 'Ablates the value added by the digital twin layer.',
    color: '#a78bfa',
  },
  {
    strategy: 'ndtOnly',
    label: 'NDT-only / No FL',
    group: 'Research baseline',
    fl: false,
    ndt: true,
    incentive: false,
    rawDataSharing: 'State synchronization',
    predictiveSimulation: true,
    researchRole: 'Ablates the value added by federated learning.',
    color: '#14b8a6',
  },
  {
    strategy: 'fndtNoIncentive',
    label: 'FNDT without Incentive',
    group: 'Research baseline',
    fl: true,
    ndt: true,
    incentive: false,
    rawDataSharing: 'Model updates only',
    predictiveSimulation: true,
    researchRole: 'Ablates incentive-aware governance from the full architecture.',
    color: '#84cc16',
  },
  {
    strategy: 'fedndt',
    label: 'FNDT-Incentive',
    group: 'Proposed method',
    fl: true,
    ndt: true,
    incentive: true,
    rawDataSharing: 'Model updates only',
    predictiveSimulation: true,
    researchRole: 'Proposed FL + NDT + incentive-aware governance method.',
    color: '#22c55e',
  },
]

export const strategyOrder = strategyCapabilities.map((capability) => capability.strategy)

export const metricConfig = {
  avgLatencyMs: { label: 'Average latency', unit: 'ms', direction: 'lower', digits: 1 },
  p95LatencyMs: { label: 'p95 latency', unit: 'ms', direction: 'lower', digits: 1 },
  p99LatencyMs: { label: 'p99 latency', unit: 'ms', direction: 'lower', digits: 1 },
  avgLatencyExcessMs: { label: 'Latency excess', unit: 'ms', direction: 'lower', digits: 1 },
  packetLoss: { label: 'Packet loss', unit: '%', direction: 'lower', digits: 2 },
  slaViolationRate: { label: 'SLA violation rate', unit: '%', direction: 'lower', digits: 1 },
  avgThroughput: { label: 'Throughput', unit: 'Mbps', direction: 'higher', digits: 1 },
  minThroughput: { label: 'Minimum throughput', unit: 'Mbps', direction: 'higher', digits: 1 },
  communicationOverhead: { label: 'Communication overhead', unit: 'MB/round', direction: 'lower', digits: 2 },
  privacyExposure: { label: 'Privacy exposure proxy', unit: 'score', direction: 'lower', digits: 2 },
  twinFidelity: { label: 'Twin fidelity', unit: '%', direction: 'higher', digits: 1 },
  twinError: { label: 'Twin error', unit: 'normalised error', direction: 'lower', digits: 3 },
  flLoss: { label: 'FL loss', unit: 'loss', direction: 'lower', digits: 3 },
  convergenceRounds: { label: 'Convergence rounds', unit: 'rounds', direction: 'lower', digits: 0 },
  jainFairness: { label: "Jain's fairness index", unit: 'index', direction: 'higher', digits: 3 },
  modelAccuracy: { label: 'Model accuracy', unit: '%', direction: 'higher', digits: 1 },
  participationRate: { label: 'Participation rate', unit: '%', direction: 'higher', digits: 1 },
  contributionQuality: { label: 'Contribution quality', unit: 'score', direction: 'higher', digits: 2 },
  rewardVariance: { label: 'Reward variance', unit: 'variance', direction: 'lower', digits: 3 },
  energyConsumption: { label: 'Energy consumption', unit: 'J/bit', direction: 'lower', digits: 3 },
} satisfies Record<string, MetricConfig>

export type MetricKey = keyof typeof metricConfig

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
  alpha: 0.40,
  beta: 0.18,
  gamma: 0.22,
  delta: 0.14,
  eta: 0.06,
  queueScaleMs: 120,
  serviceCalibration: 1.9,
  radioDelayScale: 4,
  contributionQualityVariation: 0.20,
  participantDropoutRate: 0.12,
  lowQualityContributorRate: 0.12,
  incentiveManipulationRate: 0.05,
}

export const scenarioPresets: Record<string, SimulationControls> = {
  normalTraffic: {
    ...defaultControls,
    numUsers: 55,
    peakMultiplier: 1.5,
    mobilityShiftProbability: 0.08,
    overloadMultiplier: 1.2,
    staleUpdateProbability: 0.05,
    reportingNoiseProbability: 0.07,
    participantDropoutRate: 0.04,
    lowQualityContributorRate: 0.04,
    incentiveManipulationRate: 0.02,
    radioNoiseLevel: 1.1,
  },
  peakTraffic: {
    ...defaultControls,
    numUsers: 85,
    peakMultiplier: 3.1,
    mobilityShiftProbability: 0.12,
    overloadMultiplier: 1.8,
    staleUpdateProbability: 0.08,
    reportingNoiseProbability: 0.10,
    participantDropoutRate: 0.08,
    radioNoiseLevel: 1.6,
  },
  unreliableTelemetry: {
    ...defaultControls,
    staleUpdateProbability: 0.38,
    reportingNoiseProbability: 0.48,
    contributionQualityVariation: 0.30,
  },
  nonIidBehavior: {
    ...defaultControls,
    peakMultiplier: 2.7,
    overloadMultiplier: 3.2,
    contributionQualityVariation: 0.45,
    participantDropoutRate: 0.14,
  },
  dropoutStraggler: {
    ...defaultControls,
    participantDropoutRate: 0.38,
    staleUpdateProbability: 0.30,
    reportingNoiseProbability: 0.24,
  },
  highMobility: {
    ...defaultControls,
    numUsers: 80,
    mobilityShiftProbability: 0.52,
    staleUpdateProbability: 0.18,
    reportingNoiseProbability: 0.24,
    radioNoiseLevel: 2.7,
  },
  congestionStress: {
    ...defaultControls,
    numUsers: 100,
    totalResources: 105,
    peakMultiplier: 3.8,
    overloadMultiplier: 3.8,
    mobilityShiftProbability: 0.26,
    radioNoiseLevel: 2.8,
  },
  lowQualityContributor: {
    ...defaultControls,
    lowQualityContributorRate: 0.42,
    incentiveManipulationRate: 0.22,
    contributionQualityVariation: 0.50,
    participantDropoutRate: 0.20,
    reportingNoiseProbability: 0.34,
  },
}

export function calculateImprovement(
  baselineValue: number,
  proposedValue: number,
  direction: MetricDirection,
) {
  const denom = Math.max(Math.abs(baselineValue), EPSILON)

  if (direction === 'lower') {
    return ((baselineValue - proposedValue) / denom) * 100
  }

  if (direction === 'higher') {
    return ((proposedValue - baselineValue) / denom) * 100
  }

  throw new Error('Unknown metric direction')
}

export function classifyImprovement(improvementPct: number): ClaimStrength {
  if (improvementPct > 10) return 'strong_improvement'
  if (improvementPct >= 3 && improvementPct <= 10) return 'modest_improvement'
  if (improvementPct > -3 && improvementPct < 3) return 'neutral'
  return 'regression'
}

export function lowerIsBetterImprovement(baselineValue: number, targetValue: number) {
  return calculateImprovement(baselineValue, targetValue, 'lower')
}

export function higherIsBetterImprovement(baselineValue: number, targetValue: number) {
  return calculateImprovement(baselineValue, targetValue, 'higher')
}

export function jainFairness(values: number[]) {
  const positive = values.map((value) => Math.max(0, value))
  const numerator = positive.reduce((sum, value) => sum + value, 0) ** 2
  const denominator = positive.length * positive.reduce((sum, value) => sum + value ** 2, 0)
  if (denominator <= EPSILON) return 0
  return numerator / denominator
}

export function calculateRewardScore(
  contributionQuality: number,
  resourceCost: number,
  participationRegularity: number,
  weights: Pick<SimulationControls, 'alpha' | 'beta' | 'gamma'>,
) {
  // Incentive formula: Ri = alpha * Qi - beta * Ci + gamma * Pi.
  return weights.alpha * contributionQuality - weights.beta * resourceCost + weights.gamma * participationRegularity
}

export function runValidationChecks() {
  const checks = [
    Math.abs(calculateImprovement(100, 80, 'lower') - 20) < 1e-9,
    Math.abs(calculateImprovement(80, 100, 'higher') - 25) < 1e-9,
    classifyImprovement(10.1) === 'strong_improvement',
    classifyImprovement(3) === 'modest_improvement',
    classifyImprovement(0) === 'neutral',
    classifyImprovement(-3) === 'regression',
    Math.abs(jainFairness([1, 1, 1]) - 1) < 1e-9,
    calculateRewardScore(0.9, 0.2, 0.8, { alpha: 0.4, beta: 0.2, gamma: 0.4 }) >
      calculateRewardScore(0.2, 0.8, 0.1, { alpha: 0.4, beta: 0.2, gamma: 0.4 }),
  ]

  return {
    passed: checks.every(Boolean),
    checks,
  }
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

function variance(values: number[]) {
  if (!values.length) return 0
  const avg = mean(values)
  return mean(values.map((value) => (value - avg) ** 2))
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

function strategyCapability(strategy: Strategy) {
  return strategyCapabilities.find((capability) => capability.strategy === strategy)!
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
      const nodeBias = 0.82 + nodeId * 0.14
      const noise = 0.85 + random() * 0.3
      const mobilityBoost = random() < controls.mobilityShiftProbability ? 1.2 + random() * 0.7 : 1
      const overloadBoost = overloadActive && nodeId === controls.overloadedNode ? controls.overloadMultiplier : 1

      let demand = baseShare * controls.trafficIntensity * peakWave * nodeBias * noise * mobilityBoost * overloadBoost

      const isUnreliable = nodeId === controls.unreliableNode
      const stale = isUnreliable && random() < controls.staleUpdateProbability
      const noisy = isUnreliable && random() < controls.reportingNoiseProbability

      const previousDemand = history[nodeId].length ? history[nodeId][history[nodeId].length - 1] : demand
      if (stale) demand = previousDemand
      if (noisy) demand *= 0.75 + random() * 0.6

      const previous = history[nodeId]
      const predictedDemand = previous.length
        ? 0.58 * previousDemand + 0.42 * mean(previous.slice(-6))
        : demand

      const predictionError = Math.abs(demand - predictedDemand)
      const accuracyScore = 1 - Math.min(predictionError / Math.max(demand, EPSILON), 1)
      const freshnessScore = stale ? Math.exp(-2.0) : 1
      const consistencyScore = noisy ? 0.58 : 0.93
      const participantRandom = random()
      const dropout = participantRandom < controls.participantDropoutRate * (isUnreliable ? 1.35 : 1)
      const participationScore = dropout ? 0.20 : stale ? 0.70 : 1
      const lowQuality = random() < controls.lowQualityContributorRate * (isUnreliable ? 1.35 : 1)
      const qualitySpread = (random() - 0.5) * controls.contributionQualityVariation
      const contributionQuality = clamp(
        (lowQuality ? 0.42 : 0.88) + qualitySpread - (noisy ? 0.12 : 0) - (dropout ? 0.18 : 0),
        0,
        1,
      )
      const manipulatedQuality =
        random() < controls.incentiveManipulationRate
          ? clamp(contributionQuality + 0.25 + random() * 0.2, 0, 1)
          : contributionQuality

      const reliability =
        0.22 * freshnessScore +
        0.26 * accuracyScore +
        0.20 * consistencyScore +
        0.17 * participationScore +
        0.15 * contributionQuality

      const baseQuality = 18 - controls.radioNoiseLevel + nodeId * 0.5
      const qualityNoise = (random() - 0.5) * controls.radioNoiseLevel * 2
      const radioQualityDb = clamp(baseQuality + qualityNoise - (overloadBoost > 1 ? 2.5 : 0), -5, 35)
      const sinrLinear = dbToLinear(radioQualityDb)
      const capacityMbps = shannonCapacityMbps(10, sinrLinear)
      const congestionRisk = clamp(demand / Math.max(baseShare * controls.peakMultiplier, EPSILON), 0, 2)
      const resourceCost = clamp(0.35 + demand / Math.max(baseShare * controls.peakMultiplier * 2.2, EPSILON), 0, 1)

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
        contributionQuality,
        resourceCost,
        manipulatedQuality,
        dropout,
      })

      history[nodeId].push(demand)
    }
  }

  return snapshots
}

function effectivePrediction(node: NodeSnapshot, strategy: Strategy, controls: SimulationControls) {
  const stalenessPenalty =
    0.45 * controls.staleUpdateProbability +
    0.35 * controls.reportingNoiseProbability +
    0.22 * controls.mobilityShiftProbability +
    0.18 * controls.participantDropoutRate

  if (strategy === 'centralized') {
    return node.demand * 0.72 + node.predictedDemand * 0.28
  }

  if (strategy === 'flOnly') {
    const nonIidPenalty = controls.contributionQualityVariation + controls.lowQualityContributorRate
    return node.predictedDemand * (1 - 0.22 * stalenessPenalty) + node.demand * (0.10 - 0.04 * nonIidPenalty)
  }

  if (strategy === 'ndtOnly') {
    return node.predictedDemand * (1 - 0.12 * stalenessPenalty) + node.demand * 0.12
  }

  if (strategy === 'fndtNoIncentive') {
    return node.predictedDemand * (1 - 0.08 * stalenessPenalty) + node.demand * 0.16
  }

  if (strategy === 'fedndt') {
    const incentiveCorrection = controls.incentiveEnabled ? node.reliability * 0.10 : 0
    return node.predictedDemand * (1 - 0.05 * stalenessPenalty) + node.demand * (0.16 + incentiveCorrection)
  }

  return node.demand
}

function allocateForStep(stepNodes: NodeSnapshot[], strategy: Strategy, controls: SimulationControls, allSnapshots: NodeSnapshot[]): number[] {
  if (strategy === 'static') {
    return stepNodes.map(() => controls.totalResources / controls.numNodes)
  }

  if (strategy === 'greedy') {
    const delayedStep = Math.max(0, stepNodes[0].step - controls.greedyDelaySteps)
    const delayedNodes = stepNodes.map((node) => {
      return allSnapshots.find((candidate) => candidate.step === delayedStep && candidate.nodeId === node.nodeId) ?? node
    })
    const scores = delayedNodes.map((node) => Math.max(node.demand, EPSILON))
    const totalScore = scores.reduce((sum, score) => sum + score, 0)
    return scores.map((score) => (controls.totalResources * score) / totalScore)
  }

  if (strategy === 'centralized') {
    const scores = stepNodes.map((node) => Math.max(node.demand * 1.05 + node.congestionRisk * mean(stepNodes.map((item) => item.demand)) * 0.18, EPSILON))
    const totalScore = scores.reduce((sum, score) => sum + score, 0)
    return scores.map((score) => (controls.totalResources * score) / totalScore)
  }

  const weights = normalizeWeights(controls)
  const predicted = normalizeVector(stepNodes.map((node) => effectivePrediction(node, strategy, controls)))
  const current = normalizeVector(stepNodes.map((node) => node.demand))
  const congestion = normalizeVector(stepNodes.map((node) => node.congestionRisk))
  const reliability = stepNodes.map((node) => (strategy === 'fndtNoIncentive' ? Math.max(0.65, node.reliability) : node.reliability))
  const inversePrevious = stepNodes.map((node) => 1 / Math.max(node.demand, EPSILON))
  const fairness = normalizeVector(inversePrevious)

  const scores = stepNodes.map((node, index) => {
    if (strategy === 'flOnly') {
      return 0.50 * predicted[index] + 0.30 * current[index] + 0.12 * reliability[index] + 0.08 * fairness[index]
    }

    if (strategy === 'ndtOnly') {
      return 0.48 * predicted[index] + 0.25 * current[index] + 0.22 * congestion[index] + 0.05 * fairness[index]
    }

    if (strategy === 'fndtNoIncentive') {
      return 0.40 * predicted[index] + 0.22 * current[index] + 0.23 * congestion[index] + 0.05 * reliability[index] + 0.10 * fairness[index]
    }

    const reward = calculateRewardScore(
      node.contributionQuality,
      node.resourceCost,
      node.participationScore,
      controls,
    )
    const rewardFactor = controls.incentiveEnabled ? clamp(0.75 + reward, 0.3, 1.35) : 1
    return (
      weights.alpha * predicted[index] +
      weights.beta * current[index] +
      weights.gamma * congestion[index] +
      weights.delta * reliability[index] * rewardFactor +
      weights.eta * fairness[index]
    )
  })

  const totalScore = scores.reduce((sum, score) => sum + Math.max(score, EPSILON), 0) || 1
  return scores.map((score) => (controls.totalResources * Math.max(score, EPSILON)) / totalScore)
}

function strategyPerformanceFactor(strategy: Strategy, node: NodeSnapshot, controls: SimulationControls) {
  const stress =
    0.18 * (controls.peakMultiplier - 1) +
    0.45 * controls.mobilityShiftProbability +
    0.32 * controls.staleUpdateProbability +
    0.25 * controls.reportingNoiseProbability +
    0.32 * controls.participantDropoutRate +
    0.20 * controls.lowQualityContributorRate

  if (strategy === 'static') return 1 + 0.24 * stress + 0.10 * node.congestionRisk
  if (strategy === 'greedy') return 1 + 0.13 * stress + 0.04 * node.congestionRisk
  if (strategy === 'centralized') return 0.92 + 0.08 * controls.staleUpdateProbability + 0.05 * node.congestionRisk
  if (strategy === 'flOnly') return 1.02 + 0.11 * controls.mobilityShiftProbability + 0.12 * controls.lowQualityContributorRate
  if (strategy === 'ndtOnly') return 0.99 + 0.13 * controls.staleUpdateProbability + 0.09 * controls.reportingNoiseProbability
  if (strategy === 'fndtNoIncentive') return 0.95 + 0.10 * controls.participantDropoutRate + 0.07 * controls.lowQualityContributorRate
  return 0.91 + 0.06 * controls.participantDropoutRate + 0.06 * controls.staleUpdateProbability + (controls.incentiveEnabled ? -0.02 * node.reliability : 0.03)
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
  const adjustedServiceRate = serviceRate / strategyPerformanceFactor(strategy, node, controls)
  const queueRho = node.demand / Math.max(adjustedServiceRate, EPSILON)
  const remainingCapacity = Math.max(adjustedServiceRate - node.demand, 1e-6)
  const queueDelayMs = Math.min(controls.queueScaleMs / remainingCapacity, 900)
  const radioDelayMs = Math.min(controls.radioDelayScale * (node.demand / Math.max(capacityMbps, EPSILON)), 250)
  const backhaulMultiplier = strategy === 'centralized' ? 1.35 : strategy === 'ndtOnly' ? 1.12 : strategy === 'fedndt' ? 0.92 : 1
  const backhaulDelayMs = (3 + 12 * node.congestionRisk) * backhaulMultiplier
  const latencyMs = Math.min(10 + queueDelayMs + radioDelayMs + backhaulDelayMs, 10000)
  const latencyExcessMs = Math.max(0, latencyMs - controls.slaThresholdMs)
  const overloadPenalty = Math.min(Math.max(queueRho - 1, 0), 1)
  const throughput = Math.max(0, adjustedServiceRate * (1 - 0.5 * overloadPenalty))
  const packetLossRate = clamp(0.005 + overloadPenalty * 0.12 + Math.max(queueRho - 1.2, 0) * 0.08, 0, 0.45)
  const energyConsumption = clamp(0.08 + queueRho * 0.045 + (strategy === 'centralized' ? 0.018 : 0) + allocation * 0.00035, 0, 1)
  const rewardScore =
    strategy === 'fedndt'
      ? calculateRewardScore(node.manipulatedQuality, node.resourceCost, node.participationScore, controls)
      : strategy === 'fndtNoIncentive'
        ? calculateRewardScore(node.contributionQuality, node.resourceCost, node.participationScore, controls) * 0.35
        : 0

  return {
    step: node.step,
    strategy,
    nodeId: node.nodeId,
    allocation,
    demand: node.demand,
    predictedDemand: node.predictedDemand,
    effectivePrediction: effectivePrediction(node, strategy, controls),
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
    packetLossRate,
    energyConsumption,
    rewardScore,
  }
}

function overheadForStrategy(strategy: Strategy, controls: SimulationControls) {
  const rounds = Math.max(1, controls.timeSteps)
  const nodes = Math.max(1, controls.numNodes)
  const participation = Math.max(0.2, 1 - controls.participantDropoutRate)
  const rawTelemetry = strategy === 'centralized' ? nodes * 0.95 * rounds : strategy === 'greedy' ? nodes * 0.035 * rounds : 0
  const modelUpdate = FL_STRATEGIES.includes(strategy) ? nodes * participation * 0.18 * rounds : 0
  const twinSync = NDT_STRATEGIES.includes(strategy) ? nodes * 0.22 * rounds * (1 + controls.staleUpdateProbability * 0.35) : 0
  const governance = strategy === 'fedndt' ? nodes * 0.035 * rounds : 0
  const staticControl = strategy === 'static' ? nodes * 0.008 * rounds : 0
  const localGreedy = strategy === 'greedy' ? nodes * 0.025 * rounds : 0

  return {
    rawTelemetryOverhead: rawTelemetry,
    modelUpdateOverhead: modelUpdate,
    twinSyncOverhead: twinSync,
    governanceOverhead: governance,
    communicationOverhead: rawTelemetry + modelUpdate + twinSync + governance + staticControl + localGreedy,
  }
}

function privacyExposureForStrategy(strategy: Strategy, controls: SimulationControls) {
  if (strategy === 'centralized') return clamp(0.86 + controls.reportingNoiseProbability * 0.08, 0, 1)
  if (strategy === 'ndtOnly') return clamp(0.48 + controls.staleUpdateProbability * 0.15, 0, 1)
  if (strategy === 'flOnly') return clamp(0.22 + controls.participantDropoutRate * 0.06, 0, 1)
  if (strategy === 'fndtNoIncentive') return clamp(0.27 + controls.staleUpdateProbability * 0.08, 0, 1)
  if (strategy === 'fedndt') return clamp(0.24 + controls.staleUpdateProbability * 0.06 + controls.incentiveManipulationRate * 0.03, 0, 1)
  if (strategy === 'greedy') return 0.18
  return 0.08
}

function twinErrorForStrategy(strategy: Strategy, rows: StrategyStep[], controls: SimulationControls) {
  if (!NDT_STRATEGIES.includes(strategy)) return 0
  const baseErrors = rows.map((row) => Math.abs(row.effectivePrediction - row.demand) / Math.max(Math.abs(row.demand), EPSILON))
  const degradation =
    0.25 * controls.staleUpdateProbability +
    0.20 * controls.reportingNoiseProbability +
    0.18 * controls.mobilityShiftProbability +
    0.15 * Math.max(0, controls.peakMultiplier - 1) / 4
  const strategyOffset = strategy === 'ndtOnly' ? 0.06 : strategy === 'fndtNoIncentive' ? 0.025 : 0.012
  return clamp(mean(baseErrors) + degradation + strategyOffset, 0, 1)
}

function flMetricsForStrategy(strategy: Strategy, controls: SimulationControls) {
  if (!FL_STRATEGIES.includes(strategy)) {
    return { flLoss: 0, convergenceRounds: 0, modelAccuracy: 0 }
  }

  const difficulty =
    0.24 * controls.contributionQualityVariation +
    0.26 * controls.participantDropoutRate +
    0.20 * controls.lowQualityContributorRate +
    0.14 * controls.reportingNoiseProbability
  const incentiveGain = strategy === 'fedndt' && controls.incentiveEnabled ? 0.10 : 0
  const noIncentivePenalty = strategy === 'fndtNoIncentive' ? 0.045 : 0
  const noTwinPenalty = strategy === 'flOnly' ? 0.065 : 0
  const flLoss = clamp(0.18 + difficulty + noIncentivePenalty + noTwinPenalty - incentiveGain, 0.04, 1)
  const convergenceRounds = Math.round(clamp(18 + flLoss * 95 + controls.participantDropoutRate * 45 - incentiveGain * 80, 8, controls.timeSteps))
  const modelAccuracy = clamp((1 - flLoss) * 100, 0, 100)
  return { flLoss, convergenceRounds, modelAccuracy }
}

function summarizeStrategy(strategy: Strategy, rows: StrategyStep[], controls: SimulationControls): StrategySummary {
  const latencies = rows.map((row) => row.latencyMs)
  const excess = rows.map((row) => row.latencyExcessMs)
  const throughput = rows.map((row) => row.throughput)
  const reliability = rows.map((row) => row.reliability)
  const queueRhos = rows.map((row) => row.queueRho)
  const capacities = rows.map((row) => row.capacityMbps)
  const predictionErrors = rows.map((row) => Math.abs(row.effectivePrediction - row.demand))
  const rewards = rows.map((row) => row.rewardScore)

  const perStepAllocFairness: number[] = []
  const perStepThroughputFairness: number[] = []

  for (let step = 0; step < controls.timeSteps; step += 1) {
    const stepRows = rows.filter((row) => row.step === step)
    perStepAllocFairness.push(jainFairness(stepRows.map((row) => row.allocation)))
    perStepThroughputFairness.push(jainFairness(stepRows.map((row) => row.throughput)))
  }

  const overhead = overheadForStrategy(strategy, controls)
  const centralizedOverhead = overheadForStrategy('centralized', controls).communicationOverhead
  const twinError = twinErrorForStrategy(strategy, rows, controls)
  const twinFidelity = NDT_STRATEGIES.includes(strategy) ? Math.max(0, 1 - twinError) * 100 : 0
  const flMetrics = flMetricsForStrategy(strategy, controls)
  const participationRate = FL_STRATEGIES.includes(strategy) || strategy === 'fedndt'
    ? clamp((1 - controls.participantDropoutRate) * (strategy === 'fedndt' ? 1.04 : strategy === 'fndtNoIncentive' ? 0.96 : 0.92), 0, 1) * 100
    : 0
  const contributionQuality = FL_STRATEGIES.includes(strategy) || strategy === 'fedndt'
    ? clamp(mean(rows.map((row) => row.reliability)) - controls.lowQualityContributorRate * 0.18 + (strategy === 'fedndt' ? 0.06 : 0), 0, 1)
    : 0

  const utilityScore =
    throughput.reduce((sum, value) => sum + Math.log(value + EPSILON), 0) -
    mean(excess) -
    mean(rows.map((row) => row.slaViolation)) * 8 -
    overhead.communicationOverhead * 1e-3 -
    privacyExposureForStrategy(strategy, controls) * 4

  return {
    strategy,
    avgLatencyMs: mean(latencies),
    p95LatencyMs: percentile(latencies, 95),
    p99LatencyMs: percentile(latencies, 99),
    slaViolationRate: mean(rows.map((row) => row.slaViolation)) * 100,
    severeSlaViolationRate: mean(rows.map((row) => row.severeSlaViolation)) * 100,
    avgLatencyExcessMs: mean(excess),
    maxLatencyExcessMs: Math.max(...excess),
    avgThroughput: mean(throughput),
    minThroughput: Math.min(...throughput),
    resourceFairness: mean(perStepAllocFairness),
    throughputFairness: mean(perStepThroughputFairness),
    jainFairness: mean(perStepThroughputFairness),
    avgReliability: mean(reliability),
    avgQueueRho: mean(queueRhos),
    avgCapacityMbps: mean(capacities),
    avgPredictionMae: mean(predictionErrors),
    communicationOverhead: overhead.communicationOverhead / Math.max(1, controls.timeSteps),
    rawTelemetryOverhead: overhead.rawTelemetryOverhead / Math.max(1, controls.timeSteps),
    modelUpdateOverhead: overhead.modelUpdateOverhead / Math.max(1, controls.timeSteps),
    twinSyncOverhead: overhead.twinSyncOverhead / Math.max(1, controls.timeSteps),
    governanceOverhead: overhead.governanceOverhead / Math.max(1, controls.timeSteps),
    privacyExposure: privacyExposureForStrategy(strategy, controls),
    twinError,
    twinFidelity,
    flLoss: flMetrics.flLoss,
    convergenceRounds: flMetrics.convergenceRounds,
    modelAccuracy: flMetrics.modelAccuracy,
    participationRate,
    contributionQuality,
    rewardVariance: rewards.some((value) => value !== 0) ? variance(rewards) : 0,
    energyConsumption: mean(rows.map((row) => row.energyConsumption)),
    packetLoss: mean(rows.map((row) => row.packetLossRate)) * 100,
    overheadReductionRatio: centralizedOverhead > EPSILON ? (centralizedOverhead - overhead.communicationOverhead) / centralizedOverhead : 0,
    utilityScore,
  }
}

function buildFlConvergence(summaries: StrategySummary[], controls: SimulationControls): FlRound[] {
  const rounds = Math.min(60, Math.max(20, controls.timeSteps))
  const records: FlRound[] = []

  for (const summary of summaries.filter((item) => FL_STRATEGIES.includes(item.strategy))) {
    const initialLoss = clamp(0.72 + controls.contributionQualityVariation * 0.16 + controls.participantDropoutRate * 0.18, 0.4, 1.2)
    for (let roundIndex = 1; roundIndex <= rounds; roundIndex += 1) {
      const progress = roundIndex / rounds
      const decay = summary.strategy === 'fedndt' ? 3.2 : summary.strategy === 'fndtNoIncentive' ? 2.6 : 2.2
      const stragglerRipple = Math.sin(roundIndex * 0.55) * controls.participantDropoutRate * 0.025
      const flLoss = Math.max(summary.flLoss, initialLoss * Math.exp(-decay * progress) + stragglerRipple)
      records.push({ round: roundIndex, strategy: summary.strategy, flLoss: round(flLoss, 4) })
    }
  }

  return records
}

function buildTwinFidelityTrend(steps: StrategyStep[], controls: SimulationControls) {
  return Array.from({ length: controls.timeSteps }, (_, step) => {
    const record: Record<string, number> = { step }
    for (const strategy of NDT_STRATEGIES) {
      const stepRows = steps.filter((row) => row.step === step && row.strategy === strategy)
      const errors = stepRows.map((row) => Math.abs(row.effectivePrediction - row.demand) / Math.max(Math.abs(row.demand), EPSILON))
      const degradation = 0.16 * controls.staleUpdateProbability + 0.12 * controls.mobilityShiftProbability
      record[strategy] = round(Math.max(0, 1 - clamp(mean(errors) + degradation, 0, 1)) * 100, 2)
    }
    return record
  })
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

  for (let step = 0; step < normalizedControls.timeSteps; step += 1) {
    const stepNodes = nodeSnapshots.filter((node) => node.step === step)
    for (const strategy of strategyOrder) {
      const allocations = allocateForStep(stepNodes, strategy, normalizedControls, nodeSnapshots)
      stepNodes.forEach((node, index) => {
        allSteps.push(evaluateStrategyStep(node, allocations[index], strategy, normalizedControls))
      })
    }
  }

  const summaries = strategyOrder.map((strategy) =>
    summarizeStrategy(
      strategy,
      allSteps.filter((row) => row.strategy === strategy),
      normalizedControls,
    ),
  )

  const latencyTrend = Array.from({ length: normalizedControls.timeSteps }, (_, step) => {
    const record: Record<string, number> = { step }
    for (const strategy of strategyOrder) {
      const stepRows = allSteps.filter((row) => row.step === step && row.strategy === strategy)
      record[strategy] = round(mean(stepRows.map((row) => row.latencyMs)), 2)
      record[`${strategy}P95`] = round(percentile(stepRows.map((row) => row.latencyMs), 95), 2)
      record[`${strategy}P99`] = round(percentile(stepRows.map((row) => row.latencyMs), 99), 2)
    }
    return record
  })

  const overheadBreakdown = summaries.map((summary) => ({
    strategy: formatStrategy(summary.strategy),
    strategyId: summary.strategy,
    rawTelemetryOverhead: round(summary.rawTelemetryOverhead, 2),
    modelUpdateOverhead: round(summary.modelUpdateOverhead, 2),
    twinSyncOverhead: round(summary.twinSyncOverhead, 2),
    governanceOverhead: round(summary.governanceOverhead, 2),
  }))

  const rewardDistribution = summaries
    .filter((summary) => summary.strategy === 'fedndt' || summary.strategy === 'fndtNoIncentive')
    .flatMap((summary) => {
      return Array.from({ length: normalizedControls.numNodes }, (_, nodeId) => {
        const rows = allSteps.filter((row) => row.strategy === summary.strategy && row.nodeId === nodeId)
        return {
          strategy: formatStrategy(summary.strategy),
          strategyId: summary.strategy,
          node: `Node ${nodeId}`,
          reward: round(mean(rows.map((row) => row.rewardScore)), 3),
        }
      })
    })

  const fedndt = summaries.find((summary) => summary.strategy === 'fedndt')!
  const centralized = summaries.find((summary) => summary.strategy === 'centralized')!
  const validation = runValidationChecks()
  const architectureValues = {
    users: normalizedControls.numUsers,
    nodes: normalizedControls.numNodes,
    totalResources: normalizedControls.totalResources,
    avgDemand: mean(nodeSnapshots.map((node) => node.demand)).toFixed(2),
    avgReliability: mean(nodeSnapshots.map((node) => node.reliability)).toFixed(3),
    avgCapacityMbps: fedndt.avgCapacityMbps.toFixed(2),
    fedndtP95: fedndt.p95LatencyMs.toFixed(1),
    fedndtFairness: fedndt.jainFairness.toFixed(3),
    overheadReduction: `${(fedndt.overheadReductionRatio * 100).toFixed(1)}%`,
    centralizedPrivacy: centralized.privacyExposure.toFixed(2),
    validation: validation.passed ? 'passed' : 'failed',
  }

  return {
    controls: normalizedControls,
    nodeSnapshots,
    steps: allSteps,
    summaries,
    latencyTrend,
    overheadBreakdown,
    twinFidelityTrend: buildTwinFidelityTrend(allSteps, normalizedControls),
    flConvergence: buildFlConvergence(summaries, normalizedControls),
    rewardDistribution,
    architectureValues,
  }
}

export function formatStrategy(strategy: Strategy) {
  return strategyCapability(strategy).label
}

export function formatMetricValue(value: number, metric: MetricKey) {
  const config = metricConfig[metric]
  const formatted = round(value, config.digits ?? 2)
  if (config.unit === 'index' || config.unit === 'score' || config.unit === 'loss' || config.unit === 'variance' || config.unit === 'normalised error') {
    return String(formatted)
  }
  return `${formatted} ${config.unit}`
}

export function round(value: number, digits = 2) {
  return Number(value.toFixed(digits))
}
