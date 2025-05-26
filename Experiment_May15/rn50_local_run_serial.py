import sys
import cv2
import json
import os
import time
import signal
import numpy as np


# Check if a timeout value is passed as a command-line argument
if len(sys.argv) < 2:
    print("Usage: python3 script.py <timeout_seconds>")
    sys.exit(1)

timeout = int(sys.argv[1])  # Get the timeout from the command-line argument
print(f"[INFO] Timeout set to {timeout} seconds.")

model_path = "resnet50.onnx"
label_path = "imagenet-simple-labels.json"
fifo_path = "./fallback_notify.fifo"  # Use current directory for FIFO

image_path = "000000006321.jpg"  # Fixed image to process

# ========== Setup ==========
if not os.path.exists(model_path) or not os.path.exists(label_path):
    print("Model or label file missing.", file=sys.stderr)
    sys.exit(1)

# Create FIFO in the current directory if it doesn't exist
if not os.path.exists(fifo_path):
    os.mkfifo(fifo_path)

fifo_out = open(fifo_path, "w")
print("[INFO] FIFO opened successfully.")

# ========== Model Initialization ==========
start_model_time = time.perf_counter()
model = cv2.dnn.readNetFromONNX(model_path)
with open(label_path, "r") as f:
    labels = json.load(f)
end_model_time = time.perf_counter()

model_load_time = (end_model_time - start_model_time) * 1000  # ms
print(f"[INIT] Model loaded in {model_load_time:.2f} ms")

# ========== Inference Loop ==========
inference_count = 0
inference_times = []

start_time = time.time()  # Track the start time for timeout

while True:
    # Check for timeout
    if time.time() - start_time >= timeout:
        print("[INFO] Time limit reached, exiting...")
        break

    line = sys.stdin.readline().strip()
    if not line:
        continue

    if ':' not in line:
        print(f"[ERROR] Invalid input format (expected token:image_path): {line}", file=sys.stderr)
        continue

    # This will always infer the same image "000000006321.jpg"
    token_str, _ = line.split(":", 1)  # Ignore the image path, always use the fixed image
    print(f"[INFO] Received task: {token_str}")

    if not os.path.exists(image_path):
        print(f"[ERROR] Cannot find image: {image_path}", file=sys.stderr)
        continue

    # Image processing
    start_infer_time = time.perf_counter()
    image = cv2.imread(image_path)

    if image is None:
        print(f"[ERROR] Failed to load image: {image_path}", file=sys.stderr)
        continue

    blob = cv2.dnn.blobFromImage(
        image, scalefactor=1.0/255, size=(224, 224),
        mean=(0.485, 0.456, 0.406), swapRB=True, crop=False
    )
    model.setInput(blob)
    output = model.forward()[0]
    end_infer_time = time.perf_counter()

    infer_time = (end_infer_time - start_infer_time) * 1000  # ms
    inference_times.append(infer_time)

    inference_count += 1

    # Write result to FIFO with wall-clock time
    try:
        done_time_ms = int(time.time() * 1000)
        fifo_out.write(f"{token_str},{infer_time:.2f},{done_time_ms}\n")
        fifo_out.flush()  # Ensure the data is written immediately
        print(f"[INFO] Written result to FIFO: {token_str}, {infer_time:.2f} ms")
    except Exception as e:
        print(f"[ERROR] Failed to write to FIFO: {e}", file=sys.stderr)

# ========== Summary ==========
fifo_out.close()

avg_time = np.mean(inference_times) if inference_times else 0

print("\n===== PYTHON FALLBACK SUMMARY =====")
print(f"Total images inferred:     {inference_count}")
print(f"Model load time:           {model_load_time:.2f} ms")
print(f"\nAvg inference time:        {avg_time:.2f} ms")
print("====================================")
