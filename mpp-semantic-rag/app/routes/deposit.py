from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Bin

from app.services.fusion_service import sensor_fusion
from app.services.reward_service import calculate_reward
from app.services.web3_service import mint_recycling_reward
from app.services.weight_services import stabilize_weight
from app.services.yolo_service import detect_object

router = APIRouter()

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp"
}

@router.post("/evaluate")
async def deposit_item(
    image: UploadFile = File(...),
    label: str = Form(""),
    real_weight_g: float = Form(...),
    wallet_address: str = Form(...),
    bin_id: str = Form("UNKNOWN"),
    db: Session = Depends(get_db),
):

    bin_record = (
        db.query(Bin)
        .filter(Bin.bin_code == bin_id)
        .first()
    )

    if not bin_record:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown bin: {bin_id}",
        )

    if bin_record.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=f"Bin {bin_id} is not active.",
        )
    
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only JPG, PNG, and WEBP images are accepted."
        )

    if real_weight_g <= 0:
        raise HTTPException(
            status_code=400,
            detail="Weight must be greater than zero."
        )

    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address."
        )

    transaction_id = str(uuid4())
    suffix = Path(image.filename or "upload.jpg").suffix.lower() or ".jpg"
    image_path = UPLOAD_FOLDER / f"{transaction_id}{suffix}"

    try:
        # 1. Store image with a generated safe filename.
        with image_path.open("wb") as buffer:
            buffer.write(await image.read())

        # 2. YOLO is the authoritative visual label.
        yolo_result = detect_object(str(image_path))
        detected_label = yolo_result["label"]
        confidence = round(float(yolo_result["confidence"]), 3)

        # 3. Replace this with actual load-cell readings when hardware is connected.
        stable_weight_g = stabilize_weight([real_weight_g] * 5)

        # 4. RAG semantic lookup + weight verification.
        fusion_result = sensor_fusion(
            label=detected_label,
            real_weight_g=stable_weight_g
        )

        route_signal = fusion_result["hardware_route_signal"]
        is_accepted = route_signal in {"P", "M", "E"}

        # 5. Dynamic reward calculation only for verified material.
        calculated_credits = 0.0
        reward_result = {
            "status": "SKIPPED",
            "reason": "Rejected or unverified item."
        }

        if is_accepted:
            calculated_credits = calculate_reward(
                weight_g=stable_weight_g,
                rag_result=fusion_result["rag_result"]
            )

            try:
                reward_result = mint_recycling_reward(
                    user_wallet_address=wallet_address,
                    amount_tokens=calculated_credits,
                    material=detected_label,
                    weight_grams=stable_weight_g
                )
            except Exception as exc:
                reward_result = {
                    "status": "FAILED",
                    "reason": str(exc)
                }

        tx_hash = (
            reward_result.get("tx_hash")
            or reward_result.get("transaction_hash")
        )

        explorer_url = (
            reward_result.get("explorer_url")
            or reward_result.get("etherscan_url")
        )

        return {
            "transaction_id": transaction_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS" if is_accepted else "REJECTED",
            "bin_id": bin_id,
            "predicted_label": detected_label,
            "submitted_label": label,
            "confidence": confidence,
            "stable_weight_g": stable_weight_g,
            "hardware_route_signal": route_signal,
            "fusion_result": fusion_result,
            "calculated_credits": calculated_credits,
            "web3_reward": {
                "recipient_wallet": wallet_address,
                "tokens_minted": calculated_credits,
                "status": reward_result.get("status", "UNKNOWN"),
                "tx_hash": tx_hash,
                "explorer_url": explorer_url,
                "blockchain_details": reward_result
            }
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Deposit processing failed: {str(exc)}"
        )
