from ultralytics import YOLO


# Load the YOLO model once when the server starts
model = YOLO("yolov8n.pt")


def detect_object(image_path):
    """
    Run YOLO object detection on an image.

    Parameters:
        image_path: Path of the uploaded image

    Returns:
        Dictionary containing the predicted label
        and confidence score.
    """

    results = model(image_path)

    result = results[0]

    # No object detected
    if len(result.boxes) == 0:
        return {
            "label": "no_object_detected",
            "confidence": 0.0
        }

    # Get the first detected object's class ID
    class_id = int(result.boxes.cls[0])

    # Get confidence of the detection
    confidence = float(result.boxes.conf[0])

    # Convert class ID into object name
    label = result.names[class_id]

    return {
        "label": label,
        "confidence": confidence
    }