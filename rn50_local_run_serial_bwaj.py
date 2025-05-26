import sys
import cv2
import json
import os
import time
import numpy as np

model_path = "resnet50.onnx"
label_path = "imagenet-simple-labels.json"
fifo_path = "./fallback_notify.fifo"
default_image = "000000006321.jpg"

# ========== Load Model ==========
if not os.path.exists(model_path) or not os.path.exists(label_path):
    print("Model or label file missing.", file=sys.stderr)
    sys.exit(1)

start_model_time = time.perf_counter()
model = cv2.dnn.readNetFromONNX(model_path)
with open(label_path, "r") as f:
    labels = json.load(f)
end_model_time = time.perf_counter()

model_load_time = (end_model_time - start_model_time) * 1000
print(f"[INIT] Model loaded in {model_load_time:.2f} ms")

# ========== Batch Mode ==========
if len(sys.argv) == 3 and os.path.isdir(sys.argv[1]):
    image_dir = sys.argv[1]
    try:
        max_images = int(sys.argv[2])
    except ValueError:
        print("Second argument must be an integer for number of images.")
        sys.exit(1)

    image_files = sorted([
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if os.path.isfile(os.path.join(image_dir, f))
    ])

    total_available = len(image_files)
    if max_images > total_available:
        print(f"[WARN] Requested {max_images}, only {total_available} available. Using all.")
        max_images = total_available

    image_files = image_files[:max_images]

    print(f"[INFO] Running batch inference on {max_images} images from {image_dir}")

    total_time = 0
    valid_images = 0

    for idx, image_path in enumerate(image_files):
        start = time.perf_counter()
        image = cv2.imread(image_path)
        if image is None:
            print(f"[WARN] Skipped: {image_path}")
            continue

        blob = cv2.dnn.blobFromImage(
            image, scalefactor=1.0/255, size=(224, 224),
            mean=(0.485, 0.456, 0.406), swapRB=True, crop=False
        )
        model.setInput(blob)
        _ = model.forward()[0]
        end = time.perf_counter()
        duration = (end - start) * 1000
        total_time += duration
        valid_images += 1

        print(f"[INFO] Processed {valid_images}/{max_images}: {os.path.basename(image_path)} - {duration:.2f} ms")

    avg_time = total_time / valid_images if valid_images else 0

    print("\n===== BATCH INFERENCE SUMMARY =====")
    print(f"Total images processed:    {valid_images}")
    print(f"Model load time:           {model_load_time:.2f} ms")
    print(f"Avg inference time:        {avg_time:.2f} ms")
    print("====================================")
    sys.exit(0)

# ========== Fallback Mode ==========
elif len(sys.argv) == 2:
    try:
        timeout = int(sys.argv[1])
    except ValueError:
        print("Invalid timeout value. Use: python3 script.py <timeout_seconds>")
        sys.exit(1)

    print(f"[INFO] Timeout set to {timeout} seconds.")

    if not os.path.exists(fifo_path):
        os.mkfifo(fifo_path)

    fifo_out = open(fifo_path, "w")
    print("[INFO] FIFO opened successfully.")

    inference_count = 0
    inference_times = []

    start_time = time.time()

    while True:
        if time.time() - start_time >= timeout:
            print("[INFO] Time limit reached, exiting...")
            break

        line = sys.stdin.readline().strip()
        if not line:
            continue

        if ':' not in line:
            print(f"[ERROR] Invalid input format (expected token:image_path): {line}", file=sys.stderr)
            continue

        token_str, _ = line.split(":", 1)
        print(f"[INFO] Received task: {token_str}")

        if not os.path.exists(default_image):
            print(f"[ERROR] Cannot find image: {default_image}", file=sys.stderr)
            continue

        start_infer_time = time.perf_counter()
        image = cv2.imread(default_image)

        if image is None:
            print(f"[ERROR] Failed to load image: {default_image}", file=sys.stderr)
            continue

        blob = cv2.dnn.blobFromImage(
            image, scalefactor=1.0/255, size=(224, 224),
            mean=(0.485, 0.456, 0.406), swapRB=True, crop=False
        )
        model.setInput(blob)
        _ = model.forward()[0]
        end_infer_time = time.perf_counter()

        infer_time = (end_infer_time - start_infer_time) * 1000
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

    print("\n===== PYTHON FALLBACK SUMMARY =====")
    print(f"Total images inferred:     {inference_count}")
    print(f"Model load time:           {model_load_time:.2f} ms")
    print(f"Avg inference time:        {avg_time:.2f} ms")
    print("====================================")

else:
    print("Usage:")
    print("  python3 script.py <timeout_seconds>")
    print("  python3 script.py <image_directory> <num_images>")
    sys.exit(1)
