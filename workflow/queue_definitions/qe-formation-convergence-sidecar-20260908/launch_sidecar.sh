#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PW="${PW:-$HOME/software/q-e-qe-7.5/bin/pw.x}"
RANKS="${RANKS:-12}"
POOLS="${POOLS:-2}"

if [[ ! -x "$PW" ]]; then
  echo "QE executable not found: $PW" >&2
  exit 1
fi
if pgrep -f '[r]un_convergence_queue.sh' >/dev/null; then
  echo "A convergence sidecar is already running." >&2
  exit 1
fi
EXISTING=$(pgrep -x pw.x | wc -l || true)
if [[ "$EXISTING" -gt 24 ]]; then
  echo "More than 24 pw.x processes are already active; refusing to overload the server." >&2
  exit 1
fi

cd "$ROOT"
sha256sum -c SHA256SUMS
RUN="$HOME/qe-paper-runs/formation_convergence_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUN"
printf '%s\n' "$RUN" > "$ROOT/LATEST_RUN.txt"
printf '%s\n' "RUNNING" > "$RUN/STATUS"
cp "$ROOT/JOB_ORDER.txt" "$ROOT/pseudopotential_metadata.json" "$RUN/"
{
  date --iso-8601=seconds
  uname -a
  lscpu
  free -h
  echo "Existing pw.x processes before sidecar: $EXISTING"
  sha256sum "$(readlink -f "$PW")" "$ROOT"/pseudo/*.upf "$ROOT"/inputs/*.in
} > "$RUN/environment.txt"

nohup "$ROOT/run_convergence_queue.sh" "$RUN" "$PW" "$RANKS" "$POOLS" "$ROOT" \
  > "$RUN/queue.log" 2>&1 &
PID=$!
printf '%s\n' "$PID" > "$RUN/pid"
echo "Started 12-rank convergence sidecar PID $PID"
echo "Run directory: $RUN"
