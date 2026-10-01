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
DONE_COUNT=$(find "$RUN" -mindepth 2 -maxdepth 2 -name STATUS -exec grep -l '^DONE$' {} + 2>/dev/null | wc -l)
TOTAL_COUNT=$(grep -cve '^[[:space:]]*$' "$RUN/JOB_ORDER.txt")
echo "Completed jobs: $DONE_COUNT / $TOTAL_COUNT"
tail -n 20 "$RUN/queue.log" || true
