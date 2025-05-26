import sys
import os
import time
import json
import torch
import numpy as np
from pathlib import Path

# Setup paths
FIFO_PATH = "fallback_notify.fifo"
IMAGE_PATH = "000000006321.jpg"
MODEL_PATH = "yolov5s.pt"
YOLO_DIR = Path(__file__).resolve().parent

# Timeout
if len(sys.argv) < 2:
    print("Usage: python3 yolo_fallback.py <timeout_seconds>")
    sys.exit(1)

timeout = int(sys.argv[1])
print(f"[INFO] Timeout set to {timeout} seconds.")

# Check model and image
if not os.path.exists(MODEL_PATH):
    print(f"[ERROR] Model not found: {MODEL_PATH}", file=sys.stderr)
    sys.exit(1)

if not os.path.exists(IMAGE_PATH):
    print(f"[ERROR] Image not found: {IMAGE_PATH}", file=sys.stderr)
    sys.exit(1)

# Create FIFO
if not os.path.exists(FIFO_PATH):
    os.mkfifo(FIFO_PATH)

fifo_out = open(FIFO_PATH, "w")
print("[INFO] FIFO opened successfully.")

# Load model
start_model_time = time.perf_counter()
model = torch.hub.load(str(YOLO_DIR), 'custom', path=MODEL_PATH, source='local')
model.conf = 0.25  # confidence threshold
end_model_time = time.perf_counter()
model_load_time = (end_model_time - start_model_time) * 1000
print(f"[INIT] YOLOv5s model loaded in {model_load_time:.2f} ms")

# Inference loop
inference_times = []
inference_count = 0
start_time = time.time()

while True:
    if time.time() - start_time >= timeout:
        print("[INFO] Time limit reached, exiting...")
        break

    line = sys.stdin.readline().strip()

    if not line:
        continue
    if ':' not in line:
        print(f"[ERROR] Invalid input format: {line}", file=sys.stderr)
        continue

    token_str, _ = line.split(':', 1)
    print(f"[INFO] Received task: {token_str}")

    start_infer = time.perf_counter()
    results = model(IMAGE_PATH)
    end_infer = time.perf_counter()
    infer_time = (end_infer - start_infer) * 1000
    inference_times.append(infer_time)
    inference_count += 1

    try:
        done_time_ms = int(time.time() * 1000)
        fifo_out.write(f"{token_str},{infer_time:.2f},{done_time_ms}\n")
        fifo_out.flush()
        print(f"[INFO] Written result to FIFO: {token_str}, {infer_time:.2f} ms")
    except Exception as e:
        print(f"[ERROR] Failed to write to FIFO: {e}", file=sys.stderr)

# Summary
fifo_out.close()
avg_time = np.mean(inference_times) if inference_times else 0
print("\n===== YOLOv5 FALLBACK SUMMARY =====")
print(f"Total images inferred:     {inference_count}")
print(f"Model load time:           {model_load_time:.2f} ms")
print(f"Avg inference time:        {avg_time:.2f} ms")
print("====================================")
