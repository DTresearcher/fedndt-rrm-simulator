# FedNDT-RRM Simulator

A deterministic, network-level simulator for evaluating a Federated Network Digital Twin (FedNDT) framework for incentive-aware Edge/RAN resource management.

Proposed research framing:

**A Generative AI-Assisted Federated Network Digital Twin Framework for Incentive-Aware Edge and Radio Resource Management in 5G/6G Networks.**

## Scope

This repository implements a lightweight research simulator for comparing resource-allocation strategies under controlled Edge/RAN stress scenarios.

It is designed for:

- research prototyping
- methodology development
- deterministic scenario evaluation
- paper-ready result generation
- future static web demo deployment

It does **not** claim to be a full physical-layer 5G/6G simulator.

## What the Simulator Does

The simulator includes:

1. synthetic Edge/RAN telemetry generation
2. local Network Digital Twin state construction
3. lightweight demand prediction
4. incentive/reliability scoring
5. static, greedy, and FedNDT-Incentive resource allocation
6. latency, SLA, throughput, fairness, prediction-error, overhead, and utility metrics
7. scenario-suite execution
8. paper-ready improvement analysis

## Compared Strategies

### Static

Allocates resources equally across Edge/RAN nodes.

This can produce high Jain resource fairness, but it does not adapt to demand imbalance, overloaded nodes, stale reporting, or mobility shifts.

### Greedy

Allocates resources based on observed demand.

In stress scenarios, delayed centralized observation can be used to model stale centralized awareness.

### FedNDT-Incentive

Uses local digital twin state, predicted demand, congestion risk, and incentive/reliability scores to allocate resources adaptively.

This is a proposed framework-level policy, not a proof of globally optimal network control.

## Quick Start

Install dependencies:

```bash
uv sync