#!/bin/bash

# ========== Usage ==========
# ./run_sweep.sh <total_tasks> <model> <step> <repeats>
#   total_tasks  – tasks per run, and max λ
#   model        – tag passed to ed_oms
#   step         – λ increment (e.g. 500)
#   repeats      – runs per λ to average
# ===========================

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <total_tasks> <model> <step> <repeats>"
  exit 1
fi

TOTAL=$1
MODEL=$2
STEP=$3
REPEATS=$4

PI5_HOST="bwaj@192.168.0.110"
CSV="sweep_summary.csv"
LOG_DIR="Result_May15"

ulimit -n 65356
mkdir -p "$LOG_DIR"

# CSV header
cat > "$CSV" <<EOF
model,lambda,completed,offloaded,local,avg_latency_ms,pct_local,pct_offloaded,sending_duration_ms
EOF

# sweep λ from STEP to TOTAL in steps of STEP
for LAMBDA in $(seq "$STEP" "$STEP" "$TOTAL"); do
  echo "[INFO] λ=$LAMBDA (tasks=$TOTAL, step=$STEP, repeats=$REPEATS)"

  # reset accumulators
  sum_completed=0
  sum_offloaded=0
  sum_local=0
  sum_latency=0
  sum_pct_local=0
  sum_pct_offloaded=0
  sum_sending=0

  for run in $(seq 1 $REPEATS); do
    echo "  -- run #$run/$REPEATS"
    ssh "$PI5_HOST" "pkill -9 -f ed_oms || true"

    LOG="$LOG_DIR/ED.${LAMBDA}.${TOTAL}.${MODEL}.run${run}.log"
    ssh "$PI5_HOST" \
      "ulimit -n 65356; cd ~ && source ASAP/bin/activate && ./ed_oms ${LAMBDA} ${TOTAL} ${MODEL}" \
      > "$LOG" 2>&1

    # extract this run’s stats
    read completed offloaded local avg pct_local pct_offloaded sending < <(
      awk -F: '
        /Total tasks completed/    {c=$2}
        /Tasks sent to EC/         {o=$2}
        /Tasks run locally/        {l=$2}
        /Avg latency per task/     {a=$2}
        /Percent run locally/      {pl=$2}
        /Percent offloaded/        {po=$2}
        /Sending duration/         {s=$2}
        END {
          gsub(/[^0-9.]/,"",a); gsub(/[^0-9.]/,"",pl)
          gsub(/[^0-9.]/,"",po); gsub(/[^0-9.]/,"",s)
          print c, o, l, a, pl, po, s
        }
      ' "$LOG"
    )

    # accumulate (floating sums via awk)
    sum_completed=$((sum_completed + completed))
    sum_offloaded=$((sum_offloaded + offloaded))
    sum_local=$((sum_local + local))
    sum_latency=$(awk "BEGIN {printf \"%.2f\", $sum_latency + $avg}")
    sum_pct_local=$(awk "BEGIN {printf \"%.2f\", $sum_pct_local + $pct_local}")
    sum_pct_offloaded=$(awk "BEGIN {printf \"%.2f\", $sum_pct_offloaded + $pct_offloaded}")
    sum_sending=$(awk "BEGIN {printf \"%.2f\", $sum_sending + $sending}")
  done

  # compute averages
  avg_completed=$((sum_completed / REPEATS))
  avg_offloaded=$((sum_offloaded / REPEATS))
  avg_local=$((sum_local / REPEATS))
  avg_latency=$(awk "BEGIN {printf \"%.2f\", $sum_latency / $REPEATS}")
  avg_pct_local=$(awk "BEGIN {printf \"%.2f\", $sum_pct_local / $REPEATS}")
  avg_pct_offloaded=$(awk "BEGIN {printf \"%.2f\", $sum_pct_offloaded / $REPEATS}")
  avg_sending=$(awk "BEGIN {printf \"%.2f\", $sum_sending / $REPEATS}")

  # write one averaged line
  printf "%s,%d,%d,%d,%d,%s,%s,%s,%s\n" \
    "$MODEL" "$LAMBDA" \
    "$avg_completed" "$avg_offloaded" "$avg_local" \
    "$avg_latency" "$avg_pct_local" "$avg_pct_offloaded" "$avg_sending" \
    >> "$CSV"

  echo "[INFO] Completed λ=$LAMBDA (averaged over $REPEATS runs)"
done

echo "[INFO] SWEEP DONE. Summary → $CSV"
