import sys
import cv2
import numpy as np
import json
import os
import time
import psutil

def get_resource_usage():
    cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
    memory_info = psutil.virtual_memory()
    return {
        "cpu_per_core": cpu_percent,
        "cpu_total": sum(cpu_percent),  # sum over all cores
        "mem_used_mb": (memory_info.total - memory_info.available) / (1024 * 1024)
    }

def print_usage(start_time, image_path):
    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000  # Convert to milliseconds
    usage = get_resource_usage()
    
    print(f"\n[{os.path.basename(image_path)}] Inference Time: {elapsed_ms:.2f} ms")
    print(f"  Total CPU Usage (sum over cores): {usage['cpu_total']:.2f}%")
    for i, core in enumerate(usage['cpu_per_core']):
        print(f"    - Core {i}: {core:.2f}%")
    print(f"  Memory Used: {usage['mem_used_mb']:.2f} MB")

# ====== Initialization ======
if len(sys.argv) < 2:
    print("Usage: python3 rn50_local_run.py <image1> <image2> ...")
    sys.exit(1)

model_path = "resnet50.onnx"
label_path = "imagenet-simple-labels.json"

if not os.path.exists(model_path) or not os.path.exists(label_path):
    print("Model or label file missing.")
    sys.exit(1)

model = cv2.dnn.readNetFromONNX(model_path)
with open(label_path, "r") as f:
    labels = json.load(f)

# ====== Warmup for accurate psutil.cpu_percent() ======
psutil.cpu_percent(interval=None, percpu=True)

# ====== Image Inference Loop ======
total_start = time.perf_counter()
for image_path in sys.argv[1:]:
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Failed to load {image_path}")
        continue

    start = time.perf_counter()

    blob = cv2.dnn.blobFromImage(image, scalefactor=1.0/255, size=(224, 224),
                                 mean=(0.485, 0.456, 0.406), swapRB=True, crop=False)
    model.setInput(blob)
    output = model.forward()[0]

    top_indices = np.argsort(output)[-3:][::-1]
    print(f"\n[{os.path.basename(image_path)}] Top-3 predictions:")
    for i in top_indices:
        print(f"  - {labels[i]}: {output[i]:.4f}")

    print_usage(start, image_path)

# ====== Summary ======
total_end = time.perf_counter()
total_elapsed_ms = (total_end - total_start) * 1000
print(f"\n[Summary] Total time for all images: {total_elapsed_ms:.2f} ms")
