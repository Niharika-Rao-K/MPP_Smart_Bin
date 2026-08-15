from fastapi import APIRouter, UploadFile, File, Form
import os
import shutil

from app.services.yolo_service import detect_object
from app.services.fusion_service import sensor_fusion
from app.services.weight_services import stabilize_weight
from app.services.web3_service import mint_recycling_reward

router = APIRouter()
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/deposit")
async def deposit_item(
    image: UploadFile = File(...),
    weight: float = Form(...),
    wallet_address: str = Form(default="0x0000000000000000000000000000000000000000")
):
    # 1. Save uploaded image
    file_path = os.path.join(UPLOAD_FOLDER, image.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # 2. Run YOLO object detection
    yolo_result = detect_object(file_path)
    label = yolo_result["label"]

    # 3. Stabilize the weight reading
    simulated_readings = [weight] * 5
    stable_weight = stabilize_weight(simulated_readings)

    # 4. Sensor Fusion & ChromaDB RAG Lookup
    fusion_result = sensor_fusion(label, stable_weight)
    route_signal = fusion_result["hardware_route_signal"]

    # 5. Mint Web3 Rewards if Verified Clean
    reward_result = None
    if route_signal in ["W", "M", "E"]:
        reward_result = mint_recycling_reward(wallet_address, amount_tokens=10)

    # 6. Response payload returned to camera node / dashboard
    return {
        "message": "Deposit processed",
        "image_filename": image.filename,
        "predicted_label": label,
        "confidence": round(yolo_result["confidence"], 3),
        "stable_weight_g": stable_weight,
        "hardware_route_signal": route_signal,  # 'W', 'M', 'E', or 'R'
        "fusion_result": fusion_result,
        "web3_reward": reward_result
    }
