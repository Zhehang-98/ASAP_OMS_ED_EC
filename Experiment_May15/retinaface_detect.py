import sys
from retinaface import RetinaFace

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 retinaface_detect.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    detections = RetinaFace.detect_faces(image_path)
    print(detections)
