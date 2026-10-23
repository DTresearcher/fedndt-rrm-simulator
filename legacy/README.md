# Legacy prototype (v1) — archived

This folder keeps the first prototype for the record. **It is not used for any result
reported with the paper.**

- `fedndt_rrm/`, `scripts/`, `configs/`, `tests/`: the original Python prototype. It
  compares Static, Greedy and FedNDT-Incentive only, has no federated training, and
  its forecasts used same-slot demand.
- `web/`: the original interactive web demo. Its strategy outcomes were partly set by
  per-strategy constants (performance factors, backhaul multipliers, twin-error offsets
  and closed-form FL metrics), so its numbers are illustrative only.

The current simulator is in `src/fndt/`, and is documented in `docs/MODEL.md`.
