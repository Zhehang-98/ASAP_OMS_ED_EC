#!/usr/bin/env python3
# ==============================================================================
# RetinaFace Fallback Inference Monitor
# ------------------------------------------------------------------------------
#  This script runs as a persistent "fallback inference server" that:
#    - Loads RetinaFace model once
#    - Listens for image paths on stdin (from C++ OMS system)
#    - For each image:
#        * Runs inference
#        * Measures latency, memory, per-CPU usage
#    - At exit, prints summary of:
#        * Total images
#        * Avg inference time
#        * Avg memory usage
#        * Avg per-core CPU usage
# ------------------------------------------------------------------------------
#  Usage: Only invoked via popen("python3 retinaface_detect_serial_monitor.py")
#         Image paths are piped in from C++ one line at a time.
# ==============================================================================

import sys
import time
import psutil
from retinaface import RetinaFace
from threading import Thread, Event
import numpy as np

# -------------------------------
# Global statistics & control
# -------------------------------
inference_count = 0
inference_times = []
inference_memory = []
inference_cpu = []
shutdown_event = Event()

cpu_log_buffer = []  # Background CPU usage buffer (optional)
cpu_count = psutil.cpu_count()

# ==============================================================================
# Thread: Background CPU sampler
# Records CPU usage every 10ms while inference is running
# ==============================================================================
def sample_cpu(cpu_log, interval=0.01):
    while not shutdown_event.is_set():
        cpu_log.append(psutil.cpu_percent(percpu=True))
        time.sleep(interval)

sampler = Thread(target=sample_cpu, args=(cpu_log_buffer,))
sampler.start()

# ==============================================================================
# Step 1: Load RetinaFace model and measure CPU/Memory usage
# ==============================================================================
print("[INIT] Loading RetinaFace model...", file=sys.stderr)
start_model_time = time.perf_counter()
pre_mem = psutil.Process().memory_info().rss / (1024 ** 2)

model = RetinaFace  # lazy-loaded RetinaFace wrapper
# No need to load image here; detection triggers internal load

post_mem = psutil.Process().memory_info().rss / (1024 ** 2)
end_model_time = time.perf_counter()

model_load_time = (end_model_time - start_model_time) * 1000  # ms
model_load_memory = post_mem - pre_mem
model_load_cpu_snapshot = psutil.cpu_percent(percpu=True)

print(f"[INIT] Model load time: {model_load_time:.2f} ms", file=sys.stderr)
print(f"[INIT] Model memory usage: {model_load_memory:.2f} MB", file=sys.stderr)
print(f"[INIT] CPU snapshot at model load: {model_load_cpu_snapshot}", file=sys.stderr)

# ==============================================================================
# Step 2: Main Loop  Wait for C++ to pipe in image paths
# Each line = 1 fallback image task
# ==============================================================================
for line in sys.stdin:
    image_path = line.strip()
    if not image_path:
        continue

    # --- Measure pre-inference memory ---
    pre_infer_mem = psutil.Process().memory_info().rss / (1024 ** 2)

    # --- Time inference ---
    start_time = time.perf_counter()
    detections = model.detect_faces(image_path)
    end_time = time.perf_counter()

    infer_time = (end_time - start_time) * 1000
    inference_times.append(infer_time)

    # --- Measure memory delta ---
    post_infer_mem = psutil.Process().memory_info().rss / (1024 ** 2)
    inference_memory.append(post_infer_mem - pre_infer_mem)

    # --- Sample CPU usage snapshot ---
    snapshot = psutil.cpu_percent(percpu=True)
    inference_cpu.append(snapshot)

    inference_count += 1

    print(f"\n[{image_path}] Detected {len(detections)} faces")

# ==============================================================================
# Step 3: Cleanup  Stop CPU sampler and summarize
# ==============================================================================
shutdown_event.set()
sampler.join()

avg_time = np.mean(inference_times) if inference_times else 0
avg_mem = np.mean(inference_memory) if inference_memory else 0
cpu_arr = np.array(inference_cpu)
avg_cpu_per_core = np.mean(cpu_arr, axis=0) if cpu_arr.size else np.zeros(cpu_count)
total_cpu_util = np.sum(avg_cpu_per_core)

# ==============================================================================
# Final Summary Report
# ==============================================================================
print("\n===== RETINAFACE FALLBACK SUMMARY =====")
print(f"Total images inferred:     {inference_count}")
print(f"Model load time:           {model_load_time:.2f} ms")
print(f"Model load memory used:    {model_load_memory:.2f} MB")
print(f"Model load CPU snapshot:   {model_load_cpu_snapshot}")
print(f"\nAvg inference time:        {avg_time:.2f} ms")
print(f"Avg memory per inference:  {avg_mem:.2f} MB")
print(f"\nPer-core average CPU usage during inference:")
for i, usage in enumerate(avg_cpu_per_core):
    print(f"  CPU {i}: {usage:.2f} %")
print(f"Total CPU usage (max {cpu_count * 100}%): {total_cpu_util:.2f} %")
print("========================================")
