# Paper Claims

This document separates supported claims, cautious claims, and non-claims.

## Conservative Main Claim

The proposed FedNDT-Incentive strategy reduces latency severity and tail-latency behavior under stressed network-level Edge/RAN resource-management scenarios, while raw SLA violation frequency must be interpreted together with p95/p99 latency and latency-excess severity.

## Supported Result Patterns

The current scenario-suite analysis supports these patterns:

- In stress_unreliable_nodes, FedNDT improves average latency, p95 latency, p99 latency, and average latency excess against greedy.
- In stress_unreliable_nodes, FedNDT strongly improves p95 and p99 latency against static.
- In mobility_stress, FedNDT improves average latency, p95 latency, p99 latency, and maximum latency excess against greedy.
- In overload_stress, FedNDT improves average latency, p95 latency, p99 latency, and latency excess against greedy.
- In high_noise_radio_stress, FedNDT improves average latency, p95 latency, p99 latency, and latency excess against greedy.
- In low_capacity_edge_stress, FedNDT improves average latency, p95 latency, p99 latency, and latency excess against greedy.

## Claims Requiring Caution

Do not claim:

    FedNDT always reduces SLA violation rate.

Reason:

FedNDT can have slightly higher raw SLA violation frequency while still reducing p95 latency, p99 latency, and average latency excess.

Do not claim:

    FedNDT dominates greedy in every scenario.

Reason:

Under peak_traffic, greedy can be slightly better than FedNDT for some latency metrics.

Do not claim:

    Static is best because it has high Jain resource fairness.

Reason:

Static allocation is equal, so resource fairness can be high, but equal allocation can perform poorly under uneven demand.

## Non-Claims

This work does not claim:

- full physical-layer 5G/6G simulation
- real operator network validation
- standards-compliant 5G NR scheduler implementation
- global optimality of the allocation policy
- production-ready network-control deployment
- GenAI-generated numerical results

## Recommended Paper Wording

The simulator evaluates a network-level Edge/RAN resource-management abstraction rather than a physical-layer 5G/6G waveform model. Results show that the proposed FedNDT-Incentive policy improves latency severity and tail-latency behavior under multiple stressed scenarios, particularly under unreliable reporting, mobility, overload, high radio noise, and low-capacity conditions. However, raw SLA violation frequency is not uniformly reduced, and therefore SLA results are interpreted jointly with p95/p99 latency and latency-excess severity metrics.
