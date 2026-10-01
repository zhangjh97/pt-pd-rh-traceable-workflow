#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PW="${PW:-$HOME/software/q-e-qe-7.5/bin/pw.x}"
RANKS="${RANKS:-24}"
POOLS="${POOLS:-4}"
INPUT_NAME="Pt-Pd-Rh-16_unified_pd04_vcrelax.in"

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

RUN_ROOT="$HOME/qe-paper-runs"
RUN_ID="overnight_$(date +%Y%m%d_%H%M%S)"
JOB="$RUN_ROOT/$RUN_ID"
mkdir -p "$JOB/pseudo" "$JOB/scratch"
cp "$ROOT/input/$INPUT_NAME" "$JOB/input.in"
cp "$ROOT"/pseudo/*.upf "$JOB/pseudo/"

{
  date --iso-8601=seconds
  uname -a
  lscpu
  free -h
  "$PW" -help 2>&1 | head -n 4 || true
  sha256sum "$(readlink -f "$PW")" "$JOB"/pseudo/*.upf "$JOB/input.in"
} > "$JOB/environment.txt"

printf '%q ' mpirun -np "$RANKS" "$PW" -nk "$POOLS" -in input.in > "$JOB/command.txt"
printf '\n' >> "$JOB/command.txt"
printf '%s\n' "$JOB" > "$ROOT/LATEST_RUN.txt"

cd "$JOB"
nohup env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 \
  mpirun -np "$RANKS" "$PW" -nk "$POOLS" -in input.in \
  > output.log 2>&1 &
PID=$!
printf '%s\n' "$PID" > pid
printf '%s\n' "RUNNING" > STATUS
echo "Started PID $PID"
echo "Run directory: $JOB"
echo "Maximum QE time: 39600 s (11 h); job may finish earlier."
