from ultralytics import YOLO

model = YOLO("yolov8n.pt")

def detect_object(image_path):
    results = model.predict(
        source=image_path,
        imgsz=320,
        device="cpu",
        max_det=1,
        verbose=False
    )

    result = results[0]

    if len(result.boxes) == 0:
        return {
            "label": "no_object_detected",
            "confidence": 0.0
        }

    class_id = int(result.boxes.cls[0])
    confidence = float(result.boxes.conf[0])
    label = result.names[class_id]

    return {
        "label": label,
        "confidence": confidence
    }
