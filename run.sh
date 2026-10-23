#!/usr/bin/env bash
# Full pipeline: verification tests -> confirmatory suite -> sensitivity sweeps -> statistics, report and site.
set -euo pipefail
OUT=${OUT:-results}
SEEDS=${SEEDS:-30}
SWEEP_SEEDS=${SWEEP_SEEDS:-20}
WORKERS=${WORKERS:-$(python -c "import os; print(len(os.sched_getaffinity(0)))")}
case "${1:-all}" in
  test)   python -m pytest -q tests ;;
  main)   python -m fndt.experiments main --seeds "$SEEDS" --workers "$WORKERS" --out "$OUT" ;;
  sweeps) python -m fndt.experiments sweeps --sweep-seeds "$SWEEP_SEEDS" --workers "$WORKERS" --out "$OUT" ;;
  report) python -m fndt.report --run "$OUT" && python -m fndt.site --results "$OUT" --out "$OUT/site" ;;
  all)
    mkdir -p "$OUT"
    python -m pytest -q tests | tee "$OUT/tests.log"
    python -m fndt.experiments all --seeds "$SEEDS" --sweep-seeds "$SWEEP_SEEDS" --workers "$WORKERS" --out "$OUT"
    python -m fndt.report --run "$OUT"
    python -m fndt.site --results "$OUT" --out "$OUT/site" ;;
  *) echo "usage: run.sh [test|main|sweeps|report|all]"; exit 2 ;;
esac
