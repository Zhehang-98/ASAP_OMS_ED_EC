import sys
import cv2
import numpy as np
import json
import os

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

for image_path in sys.argv[1:]:
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Failed to load {image_path}")
        continue

    blob = cv2.dnn.blobFromImage(image, scalefactor=1.0/255, size=(224, 224),
                                 mean=(0.485, 0.456, 0.406), swapRB=True, crop=False)
    model.setInput(blob)
    output = model.forward()[0]

    top_indices = np.argsort(output)[-3:][::-1]
    print(f"\n[{os.path.basename(image_path)}] Top-3 predictions:")
    for i in top_indices:
        print(f"  - {labels[i]}: {output[i]:.4f}")
