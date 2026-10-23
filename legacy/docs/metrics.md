# Metrics

## Latency Metrics

Average latency:

    avg_latency_ms = mean(latency_ms)

p95 latency:

    p95_latency_ms = 95th percentile latency

p99 latency:

    p99_latency_ms = 99th percentile latency

Average latency captures typical delay, while p95 and p99 capture tail-latency behavior.

## SLA Metrics

SLA violation rate:

    sla_violation_rate = count(latency_ms > SLA_threshold) / total_count

Severe SLA violation rate:

    severe_sla_violation_rate = count(latency_ms > 2 * SLA_threshold) / total_count

Average latency excess:

    avg_latency_excess_ms = mean(max(latency_ms - SLA_threshold, 0))

Maximum latency excess:

    max_latency_excess_ms = max(max(latency_ms - SLA_threshold, 0))

Raw SLA violation rate should not be interpreted alone. A strategy can have fewer violations but much worse tail latency.

## Throughput Metrics

Effective throughput is computed from allocated resources, radio-quality penalty, and overload penalty.

It is a network-level throughput abstraction, not a physical-layer spectral-efficiency model.

## Utilization Metrics

Resource utilization is computed as:

    resource_utilization = min(total_demand / allocated_resource_units, 1)

## Fairness Metrics

Resource fairness:

    J(resource_allocation)

Throughput fairness:

    J(effective_throughput)

Static allocation often has high resource fairness because it allocates equally. This does not mean static has better QoS.

## Prediction Error Metrics

Mean absolute error:

    MAE = mean(|y - yhat|)

Root mean squared error:

    RMSE = sqrt(mean((y - yhat)^2))

Mean absolute percentage error:

    MAPE = mean(|y - yhat| / max(|y|, epsilon))

## Communication Overhead Proxy

Centralized overhead proxy:

    O_c = number_of_nodes * state_size * frequency

Federated overhead proxy:

    O_f = participating_nodes * model_update_size * rounds

Overhead reduction ratio:

    overhead_reduction_ratio = (O_c - O_f) / O_c

This is a proxy metric, not a measured packet trace.

## Utility Score

The simulator also computes a utility-style score:

    U(t) =
        sum_j log(throughput_j + epsilon)
      - lambda_1 * mean_latency_excess
      - lambda_2 * SLA_violation_rate
      - lambda_3 * communication_overhead

For paper claims, direct latency-severity metrics are safer than the utility score.
