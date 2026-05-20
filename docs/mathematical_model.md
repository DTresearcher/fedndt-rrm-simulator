# Mathematical Model

## Modelling Position

The simulator uses recognized mathematical abstractions where suitable, while remaining lightweight and explainable.

It separates:

1. communication/networking-inspired formulas
2. simplified simulation assumptions
3. proposed framework-specific scoring and utility formulas

## Radio / Throughput Abstraction

A Shannon-Hartley-inspired throughput abstraction is:

    C_i(t) = B_i(t) log2(1 + SINR_i(t))

where:

    C_i(t)    = estimated link capacity or throughput potential
    B_i(t)    = allocated bandwidth/resource share
    SINR_i(t) = signal-to-interference-plus-noise ratio

The current simulator uses structured synthetic radio-quality variables rather than a full physical RF channel model.

A future extension can include a simplified path-loss abstraction:

    P_rx_i(t) = P_tx - PL(d_i)

    PL(d_i) = PL_0 + 10 n log10(d_i / d_0)

where:

    P_rx_i(t) = received-power abstraction
    P_tx      = transmit-power abstraction
    PL(d_i)   = path loss at distance d_i
    PL_0      = reference path loss
    n         = path-loss exponent
    d_0       = reference distance

## Queueing / Latency Abstraction

Utilization can be represented as:

    rho_j(t) = lambda_j(t) / mu_j(t)

where:

    lambda_j(t) = demand / arrival load at node j
    mu_j(t)     = service capacity from allocated resources
    rho_j(t)    = load factor

A queueing-inspired delay grows nonlinearly as demand approaches service capacity:

    D_queue_j(t) = 1 / (mu_j(t) - lambda_j(t)), where lambda_j(t) < mu_j(t)

For stable simulation, the implementation uses a controlled load-ratio delay approximation.

Total latency is interpreted as:

    D_j(t) = D_base + D_queue_j(t) + D_radio_j(t) + D_congestion_j(t)

## Federated Prediction Abstraction

FedAvg-style aggregation can be represented as:

    theta_global^(r+1) = sum_j (n_j / N) theta_j^r

where:

    theta_j = local model parameters at node j
    n_j     = local sample count at node j
    N       = total samples across participating nodes
    r       = federated round

The current simulator keeps prediction lightweight and transparent. A future version may replace it with scikit-learn or PyTorch while preserving deterministic seeds and documented hyperparameters.

## Incentive / Reliability Model

Reliability can be represented as:

    R_j(t) = w_f F_j(t) + w_a A_j(t) + w_c C_j(t) + w_s S_j(t)

subject to:

    w_f + w_a + w_c + w_s = 1
    0 <= F_j, A_j, C_j, S_j <= 1

where:

    F_j(t) = freshness score
    A_j(t) = prediction accuracy score
    C_j(t) = consistency score
    S_j(t) = participation / stability score

Prediction accuracy can be defined as:

    A_j(t) = 1 - min(|y_j(t) - yhat_j(t)| / max(y_j(t), epsilon), 1)

Freshness can be represented as:

    F_j(t) = exp(-delta_t / tau)

Consistency can be represented as:

    C_j(t) = 1 / (1 + coefficient_of_variation_j)

Participation can be represented as:

    S_j(t) = reported_steps_j / total_steps

## Allocation Score

The proposed allocation score is:

    S_j(t) =
        alpha * normalized_predicted_demand_j(t)
      + beta  * normalized_current_demand_j(t)
      + gamma * normalized_congestion_risk_j(t)
      + delta * reliability_score_j(t)
      + eta   * fairness_compensation_j(t)

subject to:

    alpha + beta + gamma + delta + eta = 1
    alpha, beta, gamma, delta, eta >= 0

Resources are allocated as:

    x_j(t) = R_total * S_j(t) / sum_k S_k(t)

This should be presented as a framework-level heuristic, not a global optimality proof.

## Utility Score

A utility-style objective is evaluated as:

    U(t) =
        sum_j log(throughput_j(t) + epsilon)
      - lambda_1 * mean_latency_excess(t)
      - lambda_2 * SLA_violation_rate(t)
      - lambda_3 * communication_overhead(t)

The utility score is useful for comparison but should not be the only headline result unless penalty weights are justified and sensitivity-tested.

## Jain Fairness Index

Fairness is measured using Jain's fairness index:

    J(x) = (sum_i x_i)^2 / (n * sum_i x_i^2)

A value close to 1 means equal distribution. However, equal resource allocation can still produce poor QoS under uneven demand, so fairness must be interpreted together with latency and throughput.
