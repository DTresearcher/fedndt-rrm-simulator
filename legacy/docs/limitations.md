# Limitations

## Not a Full 5G/6G Physical-Layer Simulator

This simulator does not implement:

- 5G NR waveform processing
- OFDM numerology
- MIMO beamforming
- HARQ
- RLC/MAC/PHY stack behavior
- standards-compliant RAN scheduling
- packet-level emulation
- real operator traffic traces

It is a network-level Edge/RAN resource-management simulator.

## Synthetic Telemetry

The telemetry is generated synthetically from scenario configuration files. It is not collected from a live mobile network.

Therefore, results should be interpreted as controlled simulation evidence, not deployment evidence.

## Simplified Radio Model

Radio quality is represented using abstract quality, interference, and noise variables. The simulator does not yet compute full SINR from detailed RF propagation.

## Simplified Queueing Model

Latency is queueing-inspired and grows nonlinearly under load, but the simulator does not implement packet-level queues.

## Lightweight Prediction Layer

The current prediction layer is intentionally transparent and lightweight. It is not a deep learning model.

## Incentive Model

The reliability/incentive score is a proposed framework-level mechanism. It needs further sensitivity analysis, parameter calibration, and validation before stronger claims can be made.

## Utility Score

The utility score depends on penalty weights. It should not be overstated unless those weights are justified and sensitivity-tested.

## SLA Interpretation

Raw SLA violation rate can be misleading. It must be interpreted together with:

- p95 latency
- p99 latency
- average latency excess
- maximum latency excess
- severe SLA violation rate

## GenAI Limitation

Generative AI must not generate numerical simulation results.

A future GenAI layer may only support explanation, interpretation, and operator assistance.

No OpenAI API key should be exposed in a browser frontend or GitHub Pages deployment.
