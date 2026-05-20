# Web Demo Plan

## Goal

Build a static GitHub Pages web demo that presents the FedNDT-RRM framework as an interactive research artifact.

The first version should run entirely in the browser with no backend.

## Technology Stack

- React
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- Framer Motion
- lucide-react
- GitHub Pages
- GitHub Actions

## Main UI Sections

1. Hero section
2. Interactive architecture diagram
3. Scenario builder
4. Simulation control panel
5. Mathematical model panel
6. Run simulation button
7. Metric cards
8. Latency charts
9. SLA and severity charts
10. Resource allocation chart
11. Node-level NDT state table
12. Incentive / reliability view
13. Fairness and utility view
14. Methodology and limitations section
15. GitHub / reproducibility section

## Architecture Diagram Components

- Simulated Edge/RAN Environment
- Telemetry Generator
- Local Network Digital Twin
- Federated Prediction Layer
- Incentive / Reliability Engine
- Resource Allocation Optimizer
- QoS and Utility Evaluation
- Optional GenAI Explanation Layer

## User Controls

The web demo should allow users to modify:

- number of users
- number of Edge/RAN nodes
- resource capacity
- bandwidth/resource units
- traffic intensity
- peak multiplier
- mobility shift probability
- overloaded node
- overload multiplier
- unreliable node
- stale update probability
- reporting noise probability
- greedy delay
- incentive enabled or disabled
- alpha, beta, gamma, delta, eta allocation weights
- SLA threshold
- radio noise/interference level
- simulation duration

## Security

No API keys should be exposed in the browser.

If a future GenAI explanation layer is added, it must be implemented through a secure backend or disabled in the static public demo.

## Positioning

The demo should be described as a browser-side educational and reproducibility artifact.

It should not be described as a production network controller, real 5G/6G physical-layer simulator, or operator-grade RAN optimizer.
