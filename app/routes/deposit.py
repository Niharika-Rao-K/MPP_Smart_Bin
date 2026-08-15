from fastapi import APIRouter, UploadFile, File, Form

import os
import shutil

from app.services.yolo_service import detect_object
from app.services.fusion_service import sensor_fusion
from app.services.weight_services import stabilize_weight


router = APIRouter()

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/deposit")
async def deposit_item(
    image: UploadFile = File(...),
    weight: float = Form(...)
):

    # --------------------------------------------------
    # 1. Save uploaded image
    # --------------------------------------------------

    file_path = os.path.join(
        UPLOAD_FOLDER,
        image.filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)


    # --------------------------------------------------
    # 2. Run YOLO object detection
    # --------------------------------------------------

    yolo_result = detect_object(file_path)


    # --------------------------------------------------
    # 3. TEMPORARY TEST LABEL
    # --------------------------------------------------
    # YOLO is currently predicting "stop sign" for
    # the Coca-Cola can.
    #
    # We are temporarily using the known profile so
    # that we can test the sensor-fusion pipeline.
    #
    # Later, this will be replaced with:
    #
    # label = yolo_result["label"]
    # --------------------------------------------------

    label = yolo_result["label"]


    # --------------------------------------------------
    # 4. Stabilize the weight
    # --------------------------------------------------

    # TEMPORARY SENSOR SIMULATION
# Later these values will come from the ESP32 + HX711.

    simulated_readings = [
        weight,
        weight,
        weight,
        weight,
        weight
    ]

    stable_weight = stabilize_weight(simulated_readings)
    


    # --------------------------------------------------
    # 5. Send label + stable weight to Sensor Fusion
    # --------------------------------------------------

    fusion_result = sensor_fusion(
        label,
        stable_weight
    )


    # --------------------------------------------------
    # 6. Return complete result
    # --------------------------------------------------

    return {
        "message": "Deposit processed",

        "image_filename": image.filename,

        # Actual YOLO prediction
        "predicted_label": yolo_result["label"],

        "confidence": round(
            yolo_result["confidence"],
            3
        ),

        # Weight information
        "raw_weight_g": weight,

        "stable_weight_g": stable_weight,

        # Final sensor-fusion result
        "fusion_result": fusion_result
    }