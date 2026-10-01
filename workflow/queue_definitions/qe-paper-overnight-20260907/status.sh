#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOB="${1:-$(cat "$ROOT/LATEST_RUN.txt")}" 
PID="$(cat "$JOB/pid")"
LOG="output.log"
if [[ -f "$JOB/CURRENT_LOG" ]]; then
  LOG="$(cat "$JOB/CURRENT_LOG")"
fi

if kill -0 "$PID" 2>/dev/null; then
  echo "RUNNING: $JOB"
else
  echo "FINISHED: $JOB"
fi

echo "Log: $JOB/$LOG"
grep -aE "iteration #|total energy|estimated scf accuracy|End of BFGS Geometry Optimization|Final enthalpy|convergence has been achieved|Maximum CPU time|JOB DONE|Error in routine" "$JOB/$LOG" | tail -n 50 || true
