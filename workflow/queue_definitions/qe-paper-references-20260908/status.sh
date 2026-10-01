#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN="${1:-$(cat "$ROOT/LATEST_RUN.txt")}" 
PID="$(cat "$RUN/pid")"
if kill -0 "$PID" 2>/dev/null; then
  echo "RUNNING: $RUN"
else
  echo "FINISHED: $RUN"
fi
echo "Queue status: $(cat "$RUN/STATUS")"
for ELEMENT in Pt Pd Rh; do
  JOB="$RUN/reference_${ELEMENT}_fcc"
  if [[ -f "$JOB/STATUS" ]]; then
    echo "reference_${ELEMENT}_fcc: $(cat "$JOB/STATUS")"
  else
    echo "reference_${ELEMENT}_fcc: PENDING"
  fi
done
tail -n 20 "$RUN/queue.log" || true
