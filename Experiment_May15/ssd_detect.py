import sys
import tensorflow as tf
import numpy as np

def load_labels(label_file):
    with open(label_file, "r") as f:
        return [line.strip() for line in f.readlines()]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 ssd_detect_simple.py <image>")
        sys.exit(1)

    image_path = sys.argv[1]
    model_path = "ssd_mobilenet_v2_320x320_coco17_tpu-8/saved_model"
    label_path = "coco-labels-2014_2017.txt"

    # Load model and labels
    model = tf.saved_model.load(model_path)
    labels = load_labels(label_path)

    # Load and preprocess image
    image = tf.keras.preprocessing.image.load_img(image_path)
    image = tf.keras.preprocessing.image.img_to_array(image)
    input_tensor = tf.image.resize(image, (320, 320))
    input_tensor = tf.cast(input_tensor, dtype=tf.uint8)
    input_tensor = tf.expand_dims(input_tensor, 0)

    # Run inference
    detections = model(input_tensor)

    # Parse results
    scores = detections["detection_scores"].numpy()[0]
    classes = detections["detection_classes"].numpy()[0].astype(int)
    boxes = detections["detection_boxes"].numpy()[0]

    print(f"\nResults for {image_path}:")
    for i in range(len(scores)):
        if scores[i] > 0.5:
            label = labels[classes[i] - 1] if 0 < classes[i] <= len(labels) else "Unknown"
            print(f" - {label}: {scores[i]*100:.2f}%")

