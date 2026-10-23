import { useCallback, useState } from 'react'
import type { MetricKey, Strategy } from './simulation/fedndtSimulation'

export type DashboardInteractionState = {
  selectedStrategies: Strategy[]
  selectedMetric: MetricKey
  selectedScenario: string
  hoveredStrategy: Strategy | null
  setSelectedMetric: (metric: MetricKey) => void
  setSelectedScenario: (scenario: string) => void
  toggleStrategySelection: (strategyId: Strategy, multiSelect?: boolean) => void
  setHoveredStrategy: (strategyId: Strategy | null) => void
  clearSelection: () => void
  isStrategyActive: (strategyId: Strategy) => boolean
  getStrategyOpacity: (strategyId: Strategy) => number
}

export function toggleStrategySelection(
  currentSelected: Strategy[],
  strategyId: Strategy,
  multiSelect = false,
) {
  if (!multiSelect) {
    return currentSelected.length === 1 && currentSelected[0] === strategyId ? [] : [strategyId]
  }

  return currentSelected.includes(strategyId)
    ? currentSelected.filter((selected) => selected !== strategyId)
    : [...currentSelected, strategyId]
}

export function isStrategyActive(
  strategyId: Strategy,
  selectedStrategies: Strategy[],
  hoveredStrategy: Strategy | null,
) {
  if (!selectedStrategies.length && !hoveredStrategy) return true
  if (hoveredStrategy) return strategyId === hoveredStrategy || selectedStrategies.includes(strategyId)
  return selectedStrategies.includes(strategyId)
}

export function getStrategyOpacity(
  strategyId: Strategy,
  selectedStrategies: Strategy[],
  hoveredStrategy: Strategy | null,
) {
  return isStrategyActive(strategyId, selectedStrategies, hoveredStrategy) ? 1 : 0.3
}

export function useDashboardInteractionState(
  initialMetric: MetricKey,
  initialScenario: string,
): DashboardInteractionState {
  const [selectedStrategies, setSelectedStrategies] = useState<Strategy[]>([])
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>(initialMetric)
  const [selectedScenario, setSelectedScenario] = useState(initialScenario)
  const [hoveredStrategy, setHoveredStrategy] = useState<Strategy | null>(null)

  const toggleSelection = useCallback((strategyId: Strategy, multiSelect = false) => {
    setSelectedStrategies((currentSelected) =>
      toggleStrategySelection(currentSelected, strategyId, multiSelect),
    )
  }, [])

  const clearSelection = useCallback(() => setSelectedStrategies([]), [])

  const active = useCallback(
    (strategyId: Strategy) => isStrategyActive(strategyId, selectedStrategies, hoveredStrategy),
    [hoveredStrategy, selectedStrategies],
  )

  const opacity = useCallback(
    (strategyId: Strategy) => getStrategyOpacity(strategyId, selectedStrategies, hoveredStrategy),
    [hoveredStrategy, selectedStrategies],
  )

  return {
    selectedStrategies,
    selectedMetric,
    selectedScenario,
    hoveredStrategy,
    setSelectedMetric,
    setSelectedScenario,
    toggleStrategySelection: toggleSelection,
    setHoveredStrategy,
    clearSelection,
    isStrategyActive: active,
    getStrategyOpacity: opacity,
  }
}
