#!/bin/bash

# ========== Usage ==========
# ./run_sweep.sh <total_tasks> <model> <step> <repeats>
#   total_tasks  – number of tasks per run
#   model        – tag passed to ed_oms
#   step         – lambda increment
#   repeats      – trials per lambda
# ===========================

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <total_tasks> <model> <step> <repeats>"
  exit 1
fi

TOTAL=$1
MODEL=$2
STEP=$3
REPEATS=$4

# PI5_HOST="bwaj@192.168.0.110"
PI5_HOST="zzrpi@192.168.0.104"
CSV="sweep_summary.csv"
LOG_DIR="Result_May18"
REMOTE_DIR="/home/zzrpi/Result_May18_ED"

ulimit -n 65356
mkdir -p "$LOG_DIR"

# CSV header
cat > "$CSV" <<EOF
model,lambda,completed,offloaded,local,avg_latency_ms,pct_local,pct_offloaded
EOF

for LAMBDA in $(seq "$STEP" "$STEP" "$TOTAL"); do
  echo "[INFO] λ=$LAMBDA (model=$MODEL, total=$TOTAL, repeats=$REPEATS)"

  sum_completed=0
  sum_offloaded=0
  sum_local=0
  sum_latency=0
  sum_pct_local=0
  sum_pct_offloaded=0

  for run in $(seq 1 "$REPEATS"); do
    echo "  -- run #$run/$REPEATS"
    ssh "$PI5_HOST" "pkill -9 -f ed_oms || true"

    LOG="$LOG_DIR/ED.${LAMBDA}.${TOTAL}.${MODEL}.run${run}.log"
    ssh "$PI5_HOST" \
      "ulimit -n 65356; cd ~ && source ASAP/bin/activate && ./ed_oms ${LAMBDA} ${TOTAL} ${MODEL}" \
      > "$LOG" 2>&1

    read completed offloaded local avg pct_local pct_offloaded < <(
      awk -F: '
        /Total tasks completed/    {c=$2}
        /Tasks sent to EC/         {o=$2}
        /Tasks run locally/        {l=$2}
        /Avg latency per task/     {a=$2}
        /Percent run locally/      {pl=$2}
        /Percent offloaded/        {po=$2}
        END {
          gsub(/[^0-9.]/,"",a); gsub(/[^0-9.]/,"",pl)
          gsub(/[^0-9.]/,"",po)
          print c, o, l, a, pl, po
        }
      ' "$LOG"
    )

    sum_completed=$((sum_completed + completed))
    sum_offloaded=$((sum_offloaded + offloaded))
    sum_local=$((sum_local + local))
    sum_latency=$(awk "BEGIN {print $sum_latency + $avg}")
    sum_pct_local=$(awk "BEGIN {print $sum_pct_local + $pct_local}")
    sum_pct_offloaded=$(awk "BEGIN {print $sum_pct_offloaded + $pct_offloaded}")
  done

  # Compute averages
  avg_completed=$((sum_completed / REPEATS))
  avg_offloaded=$((sum_offloaded / REPEATS))
  avg_local=$((sum_local / REPEATS))
  avg_latency=$(awk "BEGIN {printf \"%.2f\", $sum_latency / $REPEATS}")
  avg_pct_local=$(awk "BEGIN {printf \"%.2f\", $sum_pct_local / $REPEATS}")
  avg_pct_offloaded=$(awk "BEGIN {printf \"%.2f\", $sum_pct_offloaded / $REPEATS}")

  printf "%s,%d,%d,%d,%d,%s,%s,%s\n" \
    "$MODEL" "$LAMBDA" \
    "$avg_completed" "$avg_offloaded" "$avg_local" \
    "$avg_latency" "$avg_pct_local" "$avg_pct_offloaded" \
    >> "$CSV"

  echo "[INFO] λ=$LAMBDA done — avg latency=${avg_latency}ms"
done

echo "[INFO] Sweep complete. Results → $CSV"
