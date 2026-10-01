#!/usr/bin/env bash
set -euo pipefail

RUN="$1"
PW="$2"
RANKS="$3"
POOLS="$4"
ROOT="$5"

while IFS= read -r NAME; do
  [[ -n "$NAME" ]] || continue
  JOB="$RUN/$NAME"
  if [[ -f "$JOB/STATUS" ]] && grep -qx "DONE" "$JOB/STATUS"; then
    echo "[$(date --iso-8601=seconds)] Skipping completed $NAME"
    continue
  fi
  mkdir -p "$JOB/pseudo" "$JOB/scratch"
  cp "$ROOT/inputs/$NAME.in" "$JOB/input.in"
  cp "$ROOT"/pseudo/*.upf "$JOB/pseudo/"
  printf '%s\n' "RUNNING" > "$JOB/STATUS"
  echo "[$(date --iso-8601=seconds)] Starting $NAME"

  set +e
  (
    cd "$JOB"
    env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 \
      mpirun -np "$RANKS" "$PW" -nk "$POOLS" -in input.in \
      < /dev/null > output.log 2>&1
  )
  RC=$?
  set -e
  printf '%s\n' "$RC" > "$JOB/returncode"

  if grep -q "Error in routine" "$JOB/output.log"; then
    printf '%s\n' "FAILED" > "$JOB/STATUS"
    printf '%s\n' "FAILED" > "$RUN/STATUS"
    echo "[$(date --iso-8601=seconds)] QE error in $NAME"
    exit 1
  fi
  if [[ "$NAME" == *_alloy ]]; then
    COMPLETE_PATTERN="convergence has been achieved"
  else
    COMPLETE_PATTERN="End of BFGS Geometry Optimization"
  fi
  if [[ "$RC" -ne 0 ]] || ! grep -q "$COMPLETE_PATTERN" "$JOB/output.log" \
      || ! grep -q "JOB DONE" "$JOB/output.log"; then
    printf '%s\n' "FAILED_OR_INCOMPLETE" > "$JOB/STATUS"
    printf '%s\n' "INCOMPLETE" > "$RUN/STATUS"
    echo "[$(date --iso-8601=seconds)] Incomplete $NAME"
    exit 1
  fi

  printf '%s\n' "DONE" > "$JOB/STATUS"
  grep -aE "^!.*total energy|Final enthalpy|Total force =|P=|convergence has been achieved|End of BFGS|JOB DONE" \
    "$JOB/output.log" | tail -n 20 > "$JOB/final_summary.txt"
  echo "[$(date --iso-8601=seconds)] Completed $NAME"
done < "$ROOT/JOB_ORDER.txt"

printf '%s\n' "DONE" > "$RUN/STATUS"
echo "[$(date --iso-8601=seconds)] All convergence jobs completed"
