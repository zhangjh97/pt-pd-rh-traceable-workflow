#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PW="${PW:-$HOME/software/q-e-qe-7.5/bin/pw.x}"
RANKS="${RANKS:-24}"
POOLS="${POOLS:-4}"

if [[ ! -x "$PW" ]]; then
  echo "QE executable not found: $PW" >&2
  exit 1
fi
if pgrep -x pw.x >/dev/null || pgrep -x mpirun >/dev/null; then
  echo "Another QE or MPI task is running; refusing to overlap jobs." >&2
  exit 1
fi

cd "$ROOT"
sha256sum -c SHA256SUMS
RUN="$HOME/qe-paper-runs/unified_validation_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUN"
printf '%s\n' "$RUN" > "$ROOT/LATEST_RUN.txt"
printf '%s\n' "RUNNING" > "$RUN/STATUS"
cp "$ROOT/JOB_ORDER.txt" "$ROOT/pseudopotential_metadata.json" "$RUN/"
{
  date --iso-8601=seconds
  uname -a
  lscpu
  free -h
  sha256sum "$(readlink -f "$PW")" "$ROOT"/pseudo/*.upf "$ROOT"/inputs/*.in
} > "$RUN/environment.txt"

nohup "$ROOT/run_long_queue.sh" "$RUN" "$PW" "$RANKS" "$POOLS" "$ROOT" \
  > "$RUN/queue.log" 2>&1 &
PID=$!
printf '%s\n' "$PID" > "$RUN/pid"
echo "Started long queue PID $PID"
echo "Run directory: $RUN"
echo "Seven vc-relax jobs; each may use two 10-hour attempts when needed."
