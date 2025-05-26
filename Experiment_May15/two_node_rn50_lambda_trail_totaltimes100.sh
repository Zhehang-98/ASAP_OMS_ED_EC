#!/bin/bash

# ========================== Usage ==========================
# ./run_sweep_dual.sh <max_lambda> <model> <step> <repeats>
# ===========================================================

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <max_lambda> <model> <step> <repeats>"
  exit 1
fi

MAX_LAMBDA=$1
MODEL=$2
STEP=$3
REPEATS=$4
DURATION=100

PI5_HOST="zzrpi@192.168.0.112"
PI3_HOST="zzrpi3@192.168.0.113"
PI5_CSV="PI5_sweep_summary.csv"
PI3_CSV="PI3_sweep_summary.csv"

# Write CSV headers
echo "model,lambda,total_tasks,total_time_ms,completed,offloaded,local,avg_latency_ms,pct_local,pct_offloaded" > "$PI5_CSV"
echo "model,lambda,total_tasks,total_time_ms,completed,offloaded,local,avg_latency_ms,pct_local,pct_offloaded" > "$PI3_CSV"

for LAMBDA in $(seq "$STEP" "$STEP" "$MAX_LAMBDA"); do
  echo "[INFO] λ=$LAMBDA (model=$MODEL, duration=${DURATION}s, repeats=$REPEATS)"

  for run in $(seq 1 "$REPEATS"); do
    echo "  -- run #$run/$REPEATS"

    # Kill any prior ed_oms
    ssh "$PI5_HOST" "pkill -9 -f ed_oms || true"
    ssh "$PI3_HOST" "pkill -9 -f ed_oms || true"

    # Launch both in background, redirect stdout to local temp logs
    ssh "$PI5_HOST" \
      "ulimit -n 65356; cd ~ && source ASAP/bin/activate && ./ed_oms ${LAMBDA} ${DURATION}" > "tmp_pi5.log" 2>&1 &
    pid_pi5=$!

    ssh "$PI3_HOST" \
      "ulimit -n 65356; cd ~ && source ASAP/bin/activate && ./ed_oms ${LAMBDA} ${DURATION}" > "tmp_pi3.log" 2>&1 &
    pid_pi3=$!

    # Wait for both to finish
    wait $pid_pi5
    wait $pid_pi3

    # Parse function to extract stats from a log
    parse_log() {
      local log_file=$1
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
      ' "$log_file"
    }

    read p5_tt p5_tms p5_c p5_o p5_l p5_a p5_pl p5_po < <(parse_log tmp_pi5.log)
    read p3_tt p3_tms p3_c p3_o p3_l p3_a p3_pl p3_po < <(parse_log tmp_pi3.log)

    # Append to CSVs
    printf "%s,%d,%d,%d,%d,%d,%d,%.2f,%.2f,%.2f\n" \
      "$MODEL" "$LAMBDA" \
      "$p5_tt" "$p5_tms" "$p5_c" "$p5_o" "$p5_l" "$p5_a" "$p5_pl" "$p5_po" \
      >> "$PI5_CSV"

    printf "%s,%d,%d,%d,%d,%d,%d,%.2f,%.2f,%.2f\n" \
      "$MODEL" "$LAMBDA" \
      "$p3_tt" "$p3_tms" "$p3_c" "$p3_o" "$p3_l" "$p3_a" "$p3_pl" "$p3_po" \
      >> "$PI3_CSV"
  done

  echo "[INFO] λ=$LAMBDA done."
done

echo "[INFO] Sweep complete. Results → $PI5_CSV, $PI3_CSV"
