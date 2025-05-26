#!/bin/bash

# ========================== Usage ==========================
# ./run_sweep.sh <max_lambda> <model> <step> <repeats>
#   max_lambda   – maximum lambda value
#   model        – tag passed to ed_oms
#   step         – increment between lambda values
#   repeats      – how many trials per lambda
# ===========================================================

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <max_lambda> <model> <step> <repeats>"
  exit 1
fi

MAX_LAMBDA=$1
MODEL=$2
STEP=$3
REPEATS=$4

DURATION=100       # Fixed duration for each run (seconds)
PI5_HOST="zzrpi@192.168.0.112"
CSV="sweep_summary.csv"
LOG_DIR="Result_May18"
REMOTE_DIR="/home/zzrpi3/Result_May18_ED"

ulimit -n 65356
mkdir -p "$LOG_DIR"

# Write CSV header
cat > "$CSV" <<EOF
model,lambda,total_tasks,total_time_ms,completed,offloaded,local,avg_latency_ms,pct_local,pct_offloaded
EOF

# Sweep loop
for LAMBDA in $(seq "$STEP" "$STEP" "$MAX_LAMBDA"); do
  echo "[INFO] λ=$LAMBDA (model=$MODEL, duration=${DURATION}s, repeats=$REPEATS)"

  sum_total_tasks=0
  sum_total_time=0
  sum_completed=0
  sum_offloaded=0
  sum_local=0
  sum_latency=0
  sum_pct_local=0
  sum_pct_offloaded=0

  for run in $(seq 1 "$REPEATS"); do
    echo "  -- run #$run/$REPEATS"
    ssh "$PI5_HOST" "pkill -9 -f ed_oms || true"

    LOG="$LOG_DIR/ED.${LAMBDA}.${MODEL}.run${run}.log"
    ssh "$PI5_HOST" \
      "ulimit -n 65356; cd ~ && source ASAP/bin/activate && ./ed_oms ${LAMBDA} ${DURATION}" \
      > "$LOG" 2>&1

    # Extract final stats from log
    read total_tasks total_time completed offloaded local avg pct_local pct_offloaded < <(
      awk -F: '
        /Total tasks generated/   {gsub(/[^0-9]/,"",$2); tt=$2}
        /Total execution time/    {gsub(/[^0-9]/,"",$2); tms=$2}
        /Total tasks completed/   {gsub(/[^0-9]/,"",$2); c=$2}
        /Tasks sent to EC/        {gsub(/[^0-9]/,"",$2); o=$2}
        /Tasks run locally/       {gsub(/[^0-9]/,"",$2); l=$2}
        /Percent local/           {gsub(/[^0-9.]/,"",$2); pl=$2}
        /Percent offloaded/       {gsub(/[^0-9.]/,"",$2); po=$2}
        /Avg latency per task/    {gsub(/[^0-9.]/,"",$2); a=$2}
        END {print tt, tms, c, o, l, a, pl, po}
      ' "$LOG"
    )

    sum_total_tasks=$((sum_total_tasks + total_tasks))
    sum_total_time=$((sum_total_time + total_time))
    sum_completed=$((sum_completed + completed))
    sum_offloaded=$((sum_offloaded + offloaded))
    sum_local=$((sum_local + local))
    sum_latency=$(awk "BEGIN {print $sum_latency + $avg}")
    sum_pct_local=$(awk "BEGIN {print $sum_pct_local + $pct_local}")
    sum_pct_offloaded=$(awk "BEGIN {print $sum_pct_offloaded + $pct_offloaded}")
  done

  # Compute averages
  avg_total_tasks=$((sum_total_tasks / REPEATS))
  avg_total_time=$((sum_total_time / REPEATS))
  avg_completed=$((sum_completed / REPEATS))
  avg_offloaded=$((sum_offloaded / REPEATS))
  avg_local=$((sum_local / REPEATS))
  avg_latency=$(awk "BEGIN {printf \"%.2f\", $sum_latency / $REPEATS}")
  avg_pct_local=$(awk "BEGIN {printf \"%.2f\", $sum_pct_local / $REPEATS}")
  avg_pct_offloaded=$(awk "BEGIN {printf \"%.2f\", $sum_pct_offloaded / $REPEATS}")

  # Write to CSV
  printf "%s,%d,%d,%d,%d,%d,%d,%s,%s,%s\n" \
    "$MODEL" "$LAMBDA" \
    "$avg_total_tasks" "$avg_total_time" \
    "$avg_completed" "$avg_offloaded" "$avg_local" \
    "$avg_latency" "$avg_pct_local" "$avg_pct_offloaded" \
    >> "$CSV"

  echo "[INFO] λ=$LAMBDA done — avg latency=${avg_latency}ms"
done

echo "[INFO] Sweep complete. Results → $CSV"
