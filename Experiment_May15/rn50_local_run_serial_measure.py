import sys
import cv2
import numpy as np
import json
import os
import time
import psutil
from threading import Thread, Event

model_path = "resnet50.onnx"
label_path = "imagenet-simple-labels.json"
fifo_path = "/tmp/fallback_notify.fifo"

# ========== Setup ==========
if not os.path.exists(model_path) or not os.path.exists(label_path):
    print("Model or label file missing.", file=sys.stderr)
    sys.exit(1)

if not os.path.exists(fifo_path):
    os.mkfifo(fifo_path)

fifo_out = open(fifo_path, "w")

cpu_count = psutil.cpu_count(logical=True)
inference_count = 0
inference_times = []
inference_memory = []
inference_cpu = []

shutdown_event = Event()

def sample_cpu(cpu_log, interval=0.01):
    """Continuously sample per-CPU usage."""
    while not shutdown_event.is_set():
        cpu_log.append(psutil.cpu_percent(percpu=True))
        time.sleep(interval)

cpu_log_buffer = []
sampler = Thread(target=sample_cpu, args=(cpu_log_buffer,))
sampler.start()

# ========== Model Initialization ==========
start_model_time = time.perf_counter()
pre_mem = psutil.Process().memory_info().rss / (1024 ** 2)  # in MB
model = cv2.dnn.readNetFromONNX(model_path)
with open(label_path, "r") as f:
    labels = json.load(f)
post_mem = psutil.Process().memory_info().rss / (1024 ** 2)
end_model_time = time.perf_counter()

model_load_time = (end_model_time - start_model_time) * 1000  # ms
model_load_memory = post_mem - pre_mem
model_load_cpu_snapshot = psutil.cpu_percent(percpu=True)

print(f"[INIT] Model loaded in {model_load_time:.2f} ms")
print(f"[INIT] Memory used for model: {model_load_memory:.2f} MB")
print(f"[INIT] CPU at model load: {model_load_cpu_snapshot}")

# ========== Inference Loop ==========
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    if ':' not in line:
        print(f"[ERROR] Invalid input format (expected token:image_path): {line}", file=sys.stderr)
        continue

    token_str, image_path = line.split(":", 1)

    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Cannot load image: {image_path}", file=sys.stderr)
        continue

    pre_infer_mem = psutil.Process().memory_info().rss / (1024 ** 2)

    start_time = time.perf_counter()
    blob = cv2.dnn.blobFromImage(
        image, scalefactor=1.0/255, size=(224, 224),
        mean=(0.485, 0.456, 0.406), swapRB=True, crop=False
    )
    model.setInput(blob)
    output = model.forward()[0]
    end_time = time.perf_counter()

    infer_time = (end_time - start_time) * 1000  # ms
    inference_times.append(infer_time)

    post_infer_mem = psutil.Process().memory_info().rss / (1024 ** 2)
    inference_memory.append(post_infer_mem - pre_infer_mem)

    snapshot = psutil.cpu_percent(percpu=True)
    inference_cpu.append(snapshot)

    inference_count += 1

    # Write result to FIFO with wall-clock time
    try:
        done_time_ms = int(time.time() * 1000)
        fifo_out.write(f"{token_str},{infer_time:.2f},{done_time_ms}\n")
        fifo_out.flush()
    except Exception as e:
        print(f"[ERROR] Failed to write to FIFO: {e}", file=sys.stderr)

# ========== Summary ==========
shutdown_event.set()
sampler.join()
fifo_out.close()

avg_time = np.mean(inference_times) if inference_times else 0
avg_mem = np.mean(inference_memory) if inference_memory else 0
cpu_arr = np.array(inference_cpu)
avg_cpu_per_core = np.mean(cpu_arr, axis=0) if cpu_arr.size else np.zeros(cpu_count)
total_cpu_util = np.sum(avg_cpu_per_core)

print("\n===== PYTHON FALLBACK SUMMARY =====")
print(f"Total images inferred:     {inference_count}")
print(f"Model load time:           {model_load_time:.2f} ms")
print(f"Model load memory used:    {model_load_memory:.2f} MB")
print(f"Model load CPU snapshot:   {model_load_cpu_snapshot}")
print(f"\nAvg inference time:        {avg_time:.2f} ms")
print(f"Avg memory per inference:  {avg_mem:.2f} MB")
print(f"\nPer-core average CPU usage during inference:")
for i, usage in enumerate(avg_cpu_per_core):
    print(f"  CPU {i}: {usage:.2f} %")
print(f"Total CPU usage (max 400%): {total_cpu_util:.2f} %")
print("====================================")
