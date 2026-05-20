# Methodology

## Purpose

This repository implements a deterministic network-level simulator for studying a Federated Network Digital Twin (FedNDT) framework for incentive-aware Edge/RAN resource management.

The research framing is:

A Generative AI-Assisted Federated Network Digital Twin Framework for Incentive-Aware Edge and Radio Resource Management in 5G/6G Networks.

## Scope

The simulator models resource-management behavior at the Edge/RAN system level. It does not claim to implement a full 5G/6G physical-layer simulator, waveform simulator, packet-level emulator, or standards-compliant RAN scheduler.

The goal is to evaluate whether a FedNDT-based allocation policy can improve latency severity, tail latency, fairness, and communication-overhead behavior under controlled stress scenarios.

## Simulation Pipeline

The methodology follows this flow:

    Scenario YAML configuration
        -> Synthetic telemetry generation
        -> Local Network Digital Twin state construction
        -> Lightweight demand prediction
        -> Incentive / reliability scoring
        -> Resource allocation
        -> QoS, fairness, overhead, and utility evaluation
        -> Scenario-suite comparison
        -> Paper-ready improvement analysis

## Compared Strategies

### Static allocation

The static strategy allocates equal resource shares to Edge/RAN nodes. This can produce high Jain resource fairness, but it does not adapt to demand imbalance, overloaded nodes, stale reporting, or mobility shifts.

### Greedy allocation

The greedy strategy allocates resources based on observed demand. It represents a centralized demand-reactive baseline. In stress scenarios, observation delay can be introduced to model stale centralized awareness.

### FedNDT-Incentive allocation

The FedNDT-Incentive strategy uses digital twin state, predicted demand, congestion risk, and incentive/reliability scores to allocate resources adaptively. It is a proposed framework-level policy, not a globally optimal control proof.

## Determinism

All numerical results are produced by deterministic simulator logic using fixed random seeds and explicit YAML configuration files.

Generative AI is not used to generate numerical results. A future GenAI layer may only be used for explanation, documentation support, or operator assistance.

## Reproducibility

Run:

    uv run pytest
    uv run ruff check .
    uv run python scripts/run_scenario_suite.py
    uv run python scripts/analyze_scenario_suite.py

Main outputs:

    results/scenario_suite/scenario_comparison.csv
    results/scenario_suite_analysis/key_claim_summary.csv
    results/scenario_suite_analysis/fedndt_vs_greedy_improvements.csv
    results/scenario_suite_analysis/fedndt_vs_static_improvements.csv
