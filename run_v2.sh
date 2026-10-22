#!/usr/bin/env bash
# Full pipeline: verification tests -> confirmatory suite -> sensitivity sweeps -> statistics and report.
set -euo pipefail
OUT=${OUT:-results/v2}
SEEDS=${SEEDS:-30}
SWEEP_SEEDS=${SWEEP_SEEDS:-10}
WORKERS=${WORKERS:-$(python -c "import os; print(len(os.sched_getaffinity(0)))")}
case "${1:-all}" in
  test)   python -m pytest -q tests_v2 ;;
  main)   python -m fndt.experiments main --seeds "$SEEDS" --workers "$WORKERS" --out "$OUT" ;;
  sweeps) python -m fndt.experiments sweeps --sweep-seeds "$SWEEP_SEEDS" --workers "$WORKERS" --out "$OUT" ;;
  report) python -m fndt.report --run "$OUT" ;;
  all)
    python -m pytest -q tests_v2 | tee "${OUT}.tests.log"
    python -m fndt.experiments all --seeds "$SEEDS" --sweep-seeds "$SWEEP_SEEDS" --workers "$WORKERS" --out "$OUT"
    cp "${OUT}.tests.log" "$OUT/tests.log"
    python -m fndt.report --run "$OUT" ;;
  *) echo "usage: run_v2.sh [test|main|sweeps|report|all]"; exit 2 ;;
esac
