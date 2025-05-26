import sys
import os
import time
import json
import torch
import numpy as np
from pathlib import Path

FIFO_PATH = "fallback_notify.fifo"
MODEL_PATH = "yolov5s.pt"
YOLO_DIR = Path(__file__).resolve().parent

# ========== Model Check ==========
if not os.path.exists(MODEL_PATH):
    print(f"[ERROR] Model not found: {MODEL_PATH}", file=sys.stderr)
    sys.exit(1)

# ========== Load Model ==========
start_model_time = time.perf_counter()
model = torch.hub.load(str(YOLO_DIR), 'custom', path=MODEL_PATH, source='local')
model.conf = 0.25
model.eval()
end_model_time = time.perf_counter()
model_load_time = (end_model_time - start_model_time) * 1000
print(f"[INIT] YOLOv5s model loaded in {model_load_time:.2f} ms")

# ========== Batch Mode ==========
if len(sys.argv) == 3 and os.path.isdir(sys.argv[1]):
    image_dir = sys.argv[1]
    try:
        num_images = int(sys.argv[2])
    except ValueError:
        print("[ERROR] Second argument must be number of images.")
        sys.exit(1)

    image_files = sorted([
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if os.path.isfile(os.path.join(image_dir, f))
    ])

    if num_images > len(image_files):
        print(f"[WARN] Requested {num_images}, but only {len(image_files)} available.")
        num_images = len(image_files)

    image_files = image_files[:num_images]

    print(f"[INFO] Running batch inference on {num_images} images from {image_dir}")

    inference_times = []
    for idx, image_path in enumerate(image_files):
        start = time.perf_counter()
        results = model(image_path)
        end = time.perf_counter()
        infer_time = (end - start) * 1000
        inference_times.append(infer_time)
        print(f"[INFO] Processed {idx + 1}/{num_images}: {os.path.basename(image_path)} - {infer_time:.2f} ms")

    avg_time = np.mean(inference_times) if inference_times else 0

    print("\n===== YOLOv5 BATCH SUMMARY =====")
    print(f"Total images processed:    {len(inference_times)}")
    print(f"Model load time:           {model_load_time:.2f} ms")
    print(f"Avg inference time:        {avg_time:.2f} ms")
    print("=================================")
    sys.exit(0)

# ========== Fallback Mode ==========
if len(sys.argv) == 2:
    try:
        timeout = int(sys.argv[1])
    except ValueError:
        print("Usage: python3 yolo_fallback.py <timeout_seconds>")
        sys.exit(1)

    print(f"[INFO] Timeout set to {timeout} seconds.")

    if not os.path.exists(FIFO_PATH):
        os.mkfifo(FIFO_PATH)

    fifo_out = open(FIFO_PATH, "w")
    print("[INFO] FIFO opened successfully.")

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

        token_str, image_path = line.split(':', 1)
        print(f"[INFO] Received task: {token_str}")

        if not os.path.exists(image_path):
            print(f"[ERROR] Image not found: {image_path}", file=sys.stderr)
            continue

        start_infer = time.perf_counter()
        results = model(image_path)
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

    fifo_out.close()
    avg_time = np.mean(inference_times) if inference_times else 0
    print("\n===== YOLOv5 FALLBACK SUMMARY =====")
    print(f"Total images inferred:     {inference_count}")
    print(f"Model load time:           {model_load_time:.2f} ms")
    print(f"Avg inference time:        {avg_time:.2f} ms")
    print("====================================")
else:
    print("Usage:")
    print("  python3 yolo_fallback.py <timeout_seconds>")
    print("  python3 yolo_fallback.py <image_directory> <num_images>")
    sys.exit(1)
