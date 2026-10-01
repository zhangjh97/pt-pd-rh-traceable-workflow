#!/usr/bin/env bash
set -euo pipefail

RUN="$1"
PW="$2"
RANKS="$3"
POOLS="$4"
ROOT="$5"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-2}"

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

  COMPLETE=0
  for ATTEMPT in $(seq 1 "$MAX_ATTEMPTS"); do
    PART=$(printf '%02d' "$ATTEMPT")
    if [[ "$ATTEMPT" -gt 1 ]]; then
      sed -i "s/restart_mode = 'from_scratch'/restart_mode = 'restart'/" "$JOB/input.in"
    fi
    echo "[$(date --iso-8601=seconds)] Starting $NAME attempt $ATTEMPT/$MAX_ATTEMPTS"
    set +e
    (
      cd "$JOB"
      env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 \
        mpirun -np "$RANKS" "$PW" -nk "$POOLS" -in input.in \
        < /dev/null > "output.part${PART}.log" 2>&1
    )
    RC=$?
    set -e
    printf '%s\n' "$RC" > "$JOB/returncode.part${PART}"

    if grep -q "Error in routine" "$JOB/output.part${PART}.log"; then
      printf '%s\n' "FAILED" > "$JOB/STATUS"
      printf '%s\n' "FAILED" > "$RUN/STATUS"
      echo "[$(date --iso-8601=seconds)] QE error in $NAME"
      exit 1
    fi
    if grep -q "End of BFGS Geometry Optimization" "$JOB/output.part${PART}.log" \
        && grep -q "JOB DONE" "$JOB/output.part${PART}.log"; then
      COMPLETE=1
      break
    fi
    if [[ ! -d "$JOB/scratch" ]] || ! find "$JOB/scratch" -maxdepth 1 -type d -name '*.save' -print -quit | grep -q .; then
      printf '%s\n' "FAILED_NO_CHECKPOINT" > "$JOB/STATUS"
      printf '%s\n' "FAILED" > "$RUN/STATUS"
      echo "[$(date --iso-8601=seconds)] No restart checkpoint for $NAME"
      exit 1
    fi
    echo "[$(date --iso-8601=seconds)] Resuming $NAME from its checkpoint"
  done

  cat "$JOB"/output.part*.log > "$JOB/output.log"
  if [[ "$COMPLETE" -ne 1 ]]; then
    printf '%s\n' "INCOMPLETE_AFTER_RETRIES" > "$JOB/STATUS"
    printf '%s\n' "INCOMPLETE" > "$RUN/STATUS"
    echo "[$(date --iso-8601=seconds)] Retry limit reached for $NAME"
    exit 1
  fi

  printf '%s\n' "DONE" > "$JOB/STATUS"
  sed -n '/Begin final coordinates/,/End final coordinates/p' "$JOB/output.part${PART}.log" \
    > "$JOB/final_coordinates.txt"
  grep -aE "End of BFGS|Final enthalpy|Total force =|P=|JOB DONE" \
    "$JOB/output.part${PART}.log" | tail -n 20 > "$JOB/final_summary.txt"
  echo "[$(date --iso-8601=seconds)] Completed $NAME"
done < "$ROOT/JOB_ORDER.txt"

printf '%s\n' "DONE" > "$RUN/STATUS"
echo "[$(date --iso-8601=seconds)] All long-queue jobs completed"
