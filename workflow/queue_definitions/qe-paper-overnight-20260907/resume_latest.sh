#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOB="${1:-$(cat "$ROOT/LATEST_RUN.txt")}" 
PW="${PW:-$HOME/software/q-e-qe-7.5/bin/pw.x}"
RANKS="${RANKS:-24}"
POOLS="${POOLS:-4}"

if pgrep -x pw.x >/dev/null || pgrep -x mpirun >/dev/null; then
  echo "Another QE or MPI task is running; refusing to overlap jobs." >&2
  exit 1
fi
if [[ ! -d "$JOB/scratch" ]]; then
  echo "Restart directory not found: $JOB/scratch" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
cp "$JOB/input.in" "$JOB/input.before_resume_$STAMP.in"
sed -i "s/restart_mode = 'from_scratch'/restart_mode = 'restart'/" "$JOB/input.in"

cd "$JOB"
LOG="resume_$STAMP.log"
nohup env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 \
  mpirun -np "$RANKS" "$PW" -nk "$POOLS" -in input.in \
  > "$LOG" 2>&1 &
PID=$!
printf '%s\n' "$PID" > pid
printf '%s\n' "$LOG" > CURRENT_LOG
echo "Restarted PID $PID"
echo "Log: $JOB/$LOG"
