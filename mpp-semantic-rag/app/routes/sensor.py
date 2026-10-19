
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Bin, SensorReading

router = APIRouter()


class WeightReadingRequest(BaseModel):
    bin_id: str
    sensor_id: str = "loadcell-01"
    reading_id: str = Field(default_factory=lambda: str(uuid4()))
    weight_g: float = Field(gt=0, le=100000)


@router.post("/weight")
def receive_weight(
    payload: WeightReadingRequest,
    db: Session = Depends(get_db),
):
    bin_record = (
        db.query(Bin)
        .filter(Bin.bin_code == payload.bin_id)
        .first()
    )

    if not bin_record:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown bin: {payload.bin_id}",
        )

    if bin_record.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=f"Bin {payload.bin_id} is not active.",
        )

    existing = (
        db.query(SensorReading)
        .filter(SensorReading.reading_id == payload.reading_id)
        .first()
    )

    if existing:
        return {
            "status": "duplicate",
            "reading_id": existing.reading_id,
            "weight_g": existing.weight_g,
        }

    reading = SensorReading(
        bin_code=payload.bin_id,
        sensor_id=payload.sensor_id,
        reading_id=payload.reading_id,
        weight_g=payload.weight_g,
        created_at=datetime.now(timezone.utc),
    )

    db.add(reading)
    db.commit()
    db.refresh(reading)

    return {
        "status": "received",
        "reading_id": reading.reading_id,
        "bin_id": reading.bin_code,
        "weight_g": reading.weight_g,
        "created_at": (
            reading.created_at.isoformat()
            if reading.created_at else None
        ),
    }


@router.get("/weight/latest/{bin_id}")
def get_latest_weight(
    bin_id: str,
    db: Session = Depends(get_db),
):
    reading = (
        db.query(SensorReading)
        .filter(SensorReading.bin_code == bin_id)
        .order_by(SensorReading.id.desc())
        .first()
    )

    if not reading:
        return {
            "status": "waiting",
            "bin_id": bin_id,
            "weight_g": None,
            "reading_id": None,
        }

    return {
        "status": "received",
        "bin_id": reading.bin_code,
        "sensor_id": reading.sensor_id,
        "reading_id": reading.reading_id,
        "weight_g": reading.weight_g,
        "created_at": (
            reading.created_at.isoformat()
            if reading.created_at else None
        ),
    }
