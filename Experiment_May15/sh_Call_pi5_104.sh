#!/bin/bash

# ========== Usage ==========
# ./run_sweep.sh <total_tasks> <model>
# ===========================

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <total_tasks> <model>"
    exit 1
fi

TOTAL=$1
MODEL=$2
CSV="sweep_summary.csv"
PI5_HOST="zzrpi@192.168.0.104"

# raise local FD limit
ulimit -n 65356

# ensure output dir
mkdir -p Result_May15

# write CSV header
cat > "$CSV" <<EOF
model,lambda,completed,offloaded,local,avg_latency_ms,pct_local,pct_offloaded,sending_duration_ms
EOF

for LAMBDA in $(seq 500 500 15000); do
    echo "[INFO] λ=$LAMBDA, total=$TOTAL, model=$MODEL"

    # kill any previous ed_oms on Pi5
    ssh $PI5_HOST "pkill -9 -f ed_oms || true"

    # log path
    RPI5_LOG="Result_May15/ED.RPI5.${LAMBDA}.${TOTAL}.${MODEL}.log"

    # run on Pi5, capture its stdout/stats into local log
    ssh $PI5_HOST \
      "ulimit -n 65356; cd ~ && source ASAP/bin/activate && ./ed_oms ${LAMBDA} ${TOTAL} ${MODEL}" \
      > "$RPI5_LOG" 2>&1

    # extract stats from Pi5 log and append to CSV
    awk -F: -v model="$MODEL" -v lambda="$LAMBDA" '
      /Total tasks completed/    { completed=$2 }
      /Tasks sent to EC/         { offloaded=$2 }
      /Tasks run locally/        { local=$2 }
      /Avg latency per task/     { avg=$2 }
      /Percent run locally/      { pct_local=$2 }
      /Percent offloaded/        { pct_offloaded=$2 }
      /Sending duration/         { sending=$2 }
      END {
        gsub(/[^0-9.]/, "", avg)
        gsub(/[^0-9.]/, "", pct_local)
        gsub(/[^0-9.]/, "", pct_offloaded)
        gsub(/[^0-9.]/, "", sending)
        printf("%s,%d,%d,%d,%s,%s,%s,%s\n",
               model, lambda,
               completed, offloaded, local,
               avg, pct_local, pct_offloaded, sending)
      }
    ' "$RPI5_LOG" >> "$CSV"

    echo "[INFO] Completed λ=$LAMBDA"
done

echo "[INFO] Sweep done. Combined CSV → $CSV"
