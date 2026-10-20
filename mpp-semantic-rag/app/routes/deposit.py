
from datetime import datetime, timedelta, timezone
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
from app.database.models import Bin, Deposit, SensorReading
from app.services.fusion_service import sensor_fusion
from app.services.reward_service import calculate_reward
from app.services.web3_service import mint_recycling_reward
from app.services.yolo_service import detect_object

router = APIRouter()

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_READING_AGE = timedelta(minutes=5)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


@router.post("/evaluate")
async def deposit_item(
    image: UploadFile = File(...),
    label: str = Form(""),
    reading_id: str = Form(...),
    wallet_address: str = Form(...),
    bin_id: str = Form("UNKNOWN"),
    db: Session = Depends(get_db),
):
    # 1. Validate the bin.
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

    # 2. Validate the image and wallet.
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only JPG, PNG, and WEBP images are accepted.",
        )

    if (
        not wallet_address.startswith("0x")
        or len(wallet_address) != 42
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address.",
        )

    # 3. Retrieve the exact sensor reading.
    reading = (
        db.query(SensorReading)
        .filter(
            SensorReading.reading_id == reading_id,
            SensorReading.bin_code == bin_id,
        )
        .first()
    )

    if not reading:
        raise HTTPException(
            status_code=404,
            detail="Sensor reading not found for this bin. "
                   "Please take a new measurement.",
        )

    if reading.consumed:
        raise HTTPException(
            status_code=409,
            detail="This sensor reading has already been used. "
                   "Please take a new measurement.",
        )

    # SQLite may return a naive datetime even though the column
    # is declared timezone-aware.
    reading_time = reading.created_at

    if reading_time.tzinfo is None:
        reading_time = reading_time.replace(tzinfo=timezone.utc)

    reading_age = datetime.now(timezone.utc) - reading_time

    if reading_age < timedelta(seconds=0) or reading_age > MAX_READING_AGE:
        raise HTTPException(
            status_code=400,
            detail="Sensor reading is expired or has an invalid timestamp. "
                   "Please take a new measurement.",
        )

    measured_weight_g = float(reading.weight_g)

    if measured_weight_g <= 0:
        raise HTTPException(
            status_code=400,
            detail="The sensor reading must be greater than zero.",
        )

    transaction_id = str(uuid4())
    suffix = Path(image.filename or "upload.jpg").suffix.lower() or ".jpg"
    image_path = UPLOAD_FOLDER / f"{transaction_id}{suffix}"

    try:
        # 4. Save and validate the uploaded image.
        image_bytes = await image.read(MAX_IMAGE_BYTES + 1)

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty.",
            )

        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Image must be 5 MB or smaller.",
            )

        with image_path.open("wb") as buffer:
            buffer.write(image_bytes)

        # 5. Detect the item.
        yolo_result = detect_object(str(image_path))
        detected_label = yolo_result["label"]
        confidence = round(float(yolo_result["confidence"]), 3)

        # 6. Atomically claim this reading before reward processing.
        # Only one request can change consumed from False to True.
        claimed_count = (
            db.query(SensorReading)
            .filter(
                SensorReading.id == reading.id,
                SensorReading.consumed.is_(False),
            )
            .update(
                {SensorReading.consumed: True},
                synchronize_session=False,
            )
        )

        if claimed_count != 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="This sensor reading has already been claimed. "
                       "Please take a new measurement.",
            )

        # Commit the claim before attempting any on-chain reward.
        # This prevents the same reading from being reused if
        # reward processing or a later database operation fails.
        db.commit()

        stable_weight_g = measured_weight_g

        # 7. Sensor fusion and RAG verification.
        fusion_result = sensor_fusion(
            label=detected_label,
            real_weight_g=stable_weight_g,
        )

        route_signal = fusion_result["hardware_route_signal"]
        reward_eligible = fusion_result.get("reward_eligible", False)

        is_accepted = (
            route_signal in {"P", "M", "E"}
            and reward_eligible
        )

        # 8. Calculate and attempt to mint rewards for accepted items.
        calculated_credits = 0.0
        reward_result = {
            "status": "SKIPPED",
            "reason": "Rejected or unverified item.",
        }

        if is_accepted:
            calculated_credits = calculate_reward(
                weight_g=stable_weight_g,
                rag_result=fusion_result["rag_result"],
            )

            try:
                reward_result = mint_recycling_reward(
                    user_wallet_address=wallet_address,
                    amount_tokens=calculated_credits,
                    material=detected_label,
                    weight_grams=stable_weight_g,
                )
            except Exception as exc:
                # Preserve the evaluation even if minting fails.
                reward_result = {
                    "status": "FAILED",
                    "reason": str(exc),
                }

        tx_hash = (
            reward_result.get("tx_hash")
            or reward_result.get("transaction_hash")
        )

        explorer_url = (
            reward_result.get("explorer_url")
            or reward_result.get("etherscan_url")
        )

        # 9. Save the deposit record.
        deposit = Deposit(
            transaction_id=transaction_id,
            bin_id=bin_record.id,
            wallet_address=wallet_address,
            predicted_label=detected_label,
            confidence=confidence,
            weight_g=stable_weight_g,
            decision=fusion_result["decision"],
            hardware_route_signal=route_signal,
            reward_amount=calculated_credits,
            reward_status=reward_result.get("status", "UNKNOWN"),
            tx_hash=tx_hash,
        )

        db.add(deposit)
        db.commit()

        # 10. Return the evaluation to the frontend.
        return {
            "transaction_id": transaction_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS" if is_accepted else "REJECTED",
            "bin_id": bin_id,
            "reading_id": reading_id,
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
                "blockchain_details": reward_result,
            },
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Deposit processing failed: {str(exc)}",
        ) from exc

    finally:
        if image_path.exists():
            image_path.unlink()
