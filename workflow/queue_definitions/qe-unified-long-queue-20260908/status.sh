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
while IFS= read -r NAME; do
  [[ -n "$NAME" ]] || continue
  JOB="$RUN/$NAME"
  if [[ -f "$JOB/STATUS" ]]; then
    echo "$NAME: $(cat "$JOB/STATUS")"
  else
    echo "$NAME: PENDING"
  fi
done < "$RUN/JOB_ORDER.txt"
echo "Recent queue events:"
tail -n 20 "$RUN/queue.log" || true
