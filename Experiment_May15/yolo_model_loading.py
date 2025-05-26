import sys
import time
import torch
from pathlib import Path

# Setup paths
MODEL_PATH = "yolov5s.pt"
YOLO_DIR = Path(__file__).resolve().parent

# Check model existence
if not MODEL_PATH or not Path(MODEL_PATH).exists():
    print(f"[ERROR] Model not found: {MODEL_PATH}", file=sys.stderr)
    sys.exit(1)

# Load model and measure time
start_model_time = time.perf_counter()
model = torch.hub.load(str(YOLO_DIR), 'custom', path=MODEL_PATH, source='local')
model.conf = 0.25
end_model_time = time.perf_counter()

# Print load time
model_load_time = (end_model_time - start_model_time) * 1000
print(f"[INFO] YOLOv5s model loaded in {model_load_time:.2f} ms")
