# Scenario Suite

The scenario suite evaluates strategy behavior under controlled network-level stress conditions.

## Current Scenarios

| Scenario | Purpose |
|---|---|
| peak_traffic | Baseline peak traffic condition |
| stress_unreliable_nodes | Overload, mobility, stale updates, and noisy reporting |
| stress_unreliable_no_incentive | Same stress case with incentive disabled |
| stress_without_greedy_delay | Stress case without centralized greedy delay |
| mobility_stress | Higher mobility-shift probability |
| overload_stress | Stronger overloaded-node demand pressure |
| high_noise_radio_stress | Higher interference and radio-quality noise |
| low_capacity_edge_stress | Reduced total resource capacity |

## Run Commands

    uv run python scripts/run_scenario_suite.py
    uv run python scripts/analyze_scenario_suite.py

## Main Outputs

    results/scenario_suite/scenario_comparison.csv
    results/scenario_suite/scenario_comparison_latex_ready.csv
    results/scenario_suite/scenario_comparison_latex.tex
    results/scenario_suite_analysis/fedndt_vs_greedy_improvements.csv
    results/scenario_suite_analysis/fedndt_vs_static_improvements.csv
    results/scenario_suite_analysis/key_claim_summary.csv

## Interpretation Order

Use multiple metrics together:

1. average latency
2. p95 latency
3. p99 latency
4. average latency excess
5. maximum latency excess
6. severe SLA violation rate
7. throughput and utilization
8. Jain fairness
9. communication overhead
10. utility score

## Main Pattern

The scenario suite shows that FedNDT-Incentive is most useful under stressed conditions such as unreliable reporting, mobility, overload, high radio noise, and low capacity.

Under peak traffic, greedy can be slightly better than FedNDT for some latency metrics. This should be reported honestly.

## Safe Scenario Claim

Avoid:

    FedNDT always dominates all baselines.

Prefer:

    FedNDT-Incentive reduces latency severity and tail latency under several stressed network-level Edge/RAN resource-management scenarios.
