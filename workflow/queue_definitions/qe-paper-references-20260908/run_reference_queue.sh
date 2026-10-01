#!/usr/bin/env bash
set -euo pipefail

RUN="$1"
PW="$2"
RANKS="$3"
POOLS="$4"
ROOT="$5"

for ELEMENT in Pt Pd Rh; do
  JOB="$RUN/reference_${ELEMENT}_fcc"
  mkdir -p "$JOB/pseudo" "$JOB/scratch"
  cp "$ROOT/inputs/reference_${ELEMENT}_fcc.in" "$JOB/input.in"
  cp "$ROOT/pseudo/${ELEMENT}_std.upf" "$JOB/pseudo/"
  printf '%s\n' "RUNNING" > "$JOB/STATUS"
  echo "[$(date --iso-8601=seconds)] Starting reference_${ELEMENT}_fcc"
  set +e
  (
    cd "$JOB"
    env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 \
      mpirun -np "$RANKS" "$PW" -nk "$POOLS" -in input.in \
      > output.log 2>&1
  )
  RC=$?
  set -e
  printf '%s\n' "$RC" > "$JOB/returncode"
  if [[ "$RC" -eq 0 ]] && grep -q "End of BFGS Geometry Optimization" "$JOB/output.log" \
      && grep -q "JOB DONE" "$JOB/output.log"; then
    printf '%s\n' "DONE" > "$JOB/STATUS"
    sed -n '/Begin final coordinates/,/End final coordinates/p' "$JOB/output.log" \
      > "$JOB/final_coordinates.txt"
    echo "[$(date --iso-8601=seconds)] Completed reference_${ELEMENT}_fcc"
  else
    printf '%s\n' "FAILED_OR_INCOMPLETE" > "$JOB/STATUS"
    printf '%s\n' "FAILED_OR_INCOMPLETE" > "$RUN/STATUS"
    echo "[$(date --iso-8601=seconds)] Stopped after reference_${ELEMENT}_fcc"
    exit 1
  fi
done

printf '%s\n' "DONE" > "$RUN/STATUS"
echo "[$(date --iso-8601=seconds)] All elemental references completed"
