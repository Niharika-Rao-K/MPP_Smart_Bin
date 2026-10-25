
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    Bin,
    MeasurementRequest,
    SensorReading,
    SegregationCommand,
)

router = APIRouter()

REQUEST_TIMEOUT = timedelta(seconds=90)


class WeightReadingRequest(BaseModel):
    bin_id: str
    sensor_id: str = "loadcell-01"
    reading_id: str = Field(default_factory=lambda: str(uuid4()))
    weight_g: float = Field(gt=0, le=100000)


class MeasurementRequestBody(BaseModel):
    bin_id: str


class MeasurementResultBody(BaseModel):
    bin_id: str
    sensor_id: str = "loadcell-01"
    weight_g: float = Field(gt=0, le=100000)


def utc_now():
    return datetime.now(timezone.utc)


def normalize_datetime(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def validate_active_bin(db: Session, bin_id: str):
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

    return bin_record


def expire_old_requests(db: Session, bin_id: str):
    now = utc_now()

    requests = (
        db.query(MeasurementRequest)
        .filter(
            MeasurementRequest.bin_code == bin_id,
            MeasurementRequest.status.in_(["pending", "claimed", "ready", "measuring"]),
        )
        .all()
    )

    for request in requests:
        created = normalize_datetime(request.created_at)

        if now - created > REQUEST_TIMEOUT:
            request.status = "expired"

    db.commit()

class SegregationCompletionBody(BaseModel):
    status: str = Field(pattern="^completed$")


class SegregationPlacementBody(BaseModel):
    bin_id: str
# ------------------------------------------------------------
# 1. DASHBOARD: CREATE A MEASUREMENT REQUEST
# POST /api/sensor/requests
# ------------------------------------------------------------

@router.post("/requests")
def create_measurement_request(
    payload: MeasurementRequestBody,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, payload.bin_id)
    expire_old_requests(db, payload.bin_id)

    existing = (
        db.query(MeasurementRequest)
        .filter(
            MeasurementRequest.bin_code == payload.bin_id,
            MeasurementRequest.status.in_(["pending", "claimed", "ready", "measuring"]),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "This bin already has a measurement in progress. "
                "Wait for it to finish or expire."
            ),
        )

    request_id = str(uuid4())

    request = MeasurementRequest(
        request_id=request_id,
        bin_code=payload.bin_id,
        status="pending",
        created_at=utc_now(),
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return {
        "status": "pending",
        "request_id": request.request_id,
        "bin_id": request.bin_code,
        "created_at": request.created_at.isoformat(),
    }


# ------------------------------------------------------------
# 2. ESP32: CLAIM THE NEXT PENDING REQUEST
# GET /api/sensor/requests/next?bin_id=BIN001
# ------------------------------------------------------------

@router.get("/requests/next")
def get_next_measurement_request(
    bin_id: str,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, bin_id)
    expire_old_requests(db, bin_id)

    request = (
        db.query(MeasurementRequest)
        .filter(
            MeasurementRequest.bin_code == bin_id,
            MeasurementRequest.status == "pending",
        )
        .order_by(MeasurementRequest.id.asc())
        .first()
    )

    if not request:
        return {
            "status": "waiting",
            "request_id": None,
            "bin_id": bin_id,
        }

    # Claim the request with a conditional update to reduce
    # the chance of two polling devices claiming the same request.
    claimed_count = (
        db.query(MeasurementRequest)
        .filter(
            MeasurementRequest.id == request.id,
            MeasurementRequest.status == "pending",
        )
        .update(
            {
                MeasurementRequest.status: "claimed",
                MeasurementRequest.claimed_at: utc_now(),
            },
            synchronize_session=False,
        )
    )

    db.commit()

    if claimed_count != 1:
        return {
            "status": "waiting",
            "request_id": None,
            "bin_id": bin_id,
        }

    return {
        "status": "claimed",
        "request_id": request.request_id,
        "bin_id": request.bin_code,
        "sensor_id": "loadcell-01",
    }


# ------------------------------------------------------------
# 3. ESP32: SUBMIT THE MEASUREMENT
# POST /api/sensor/requests/{request_id}/reading
# ------------------------------------------------------------

# ESP32 signals that the empty platform has been tared.
@router.post("/requests/{request_id}/ready")
def mark_measurement_ready(
    request_id: str,
    db: Session = Depends(get_db),
):
    request = (
        db.query(MeasurementRequest)
        .filter(MeasurementRequest.request_id == request_id)
        .first()
    )

    if not request:
        raise HTTPException(status_code=404, detail="Measurement request not found.")

    validate_active_bin(db, request.bin_code)

    if request.status != "claimed":
        raise HTTPException(
            status_code=409,
            detail=f"Request cannot become ready from status: {request.status}",
        )

    if utc_now() - normalize_datetime(request.created_at) > REQUEST_TIMEOUT:
        request.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Measurement request expired.")

    request.status = "ready"
    db.commit()

    return {
        "status": "ready",
        "request_id": request.request_id,
        "bin_id": request.bin_code,
    }


# Dashboard authorizes weighing after the user confirms item placement.
@router.post("/requests/{request_id}/confirm")
def confirm_measurement(
    request_id: str,
    db: Session = Depends(get_db),
):
    request = (
        db.query(MeasurementRequest)
        .filter(MeasurementRequest.request_id == request_id)
        .first()
    )

    if not request:
        raise HTTPException(status_code=404, detail="Measurement request not found.")

    validate_active_bin(db, request.bin_code)

    if request.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Request is not ready for confirmation: {request.status}",
        )

    if utc_now() - normalize_datetime(request.created_at) > REQUEST_TIMEOUT:
        request.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Measurement request expired.")

    request.status = "measuring"
    db.commit()

    return {
        "status": "measuring",
        "request_id": request.request_id,
        "bin_id": request.bin_code,
    }

@router.post("/requests/{request_id}/reading")
def submit_requested_measurement(
    request_id: str,
    payload: MeasurementResultBody,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, payload.bin_id)

    request = (
        db.query(MeasurementRequest)
        .filter(
            MeasurementRequest.request_id == request_id,
            MeasurementRequest.bin_code == payload.bin_id,
        )
        .first()
    )

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Measurement request not found for this bin.",
        )

    if request.status != "measuring":
        raise HTTPException(
            status_code=409,
            detail=f"Request is not authorized for weighing: {request.status}",
        )

    created = normalize_datetime(request.created_at)

    if utc_now() - created > REQUEST_TIMEOUT:
        request.status = "expired"
        db.commit()

        raise HTTPException(
            status_code=410,
            detail="Measurement request expired. Please try again.",
        )

    existing = (
        db.query(SensorReading)
        .filter(SensorReading.reading_id == request_id)
        .first()
    )

    if existing:
        request.status = "completed"
        db.commit()

        return {
            "status": "completed",
            "request_id": request_id,
            "reading_id": existing.reading_id,
            "weight_g": existing.weight_g,
        }

    reading = SensorReading(
        bin_code=payload.bin_id,
        sensor_id=payload.sensor_id,
        reading_id=request_id,
        weight_g=payload.weight_g,
        consumed=False,
        created_at=utc_now(),
    )

    request.status = "completed"

    db.add(reading)
    db.commit()
    db.refresh(reading)

    return {
        "status": "completed",
        "request_id": request_id,
        "reading_id": reading.reading_id,
        "bin_id": reading.bin_code,
        "weight_g": reading.weight_g,
    }


# ------------------------------------------------------------
# 4. DASHBOARD: CHECK A SPECIFIC REQUEST
# GET /api/sensor/requests/{request_id}
# ------------------------------------------------------------

@router.get("/requests/{request_id}")
def get_measurement_request_status(
    request_id: str,
    db: Session = Depends(get_db),
):
    request = (
        db.query(MeasurementRequest)
        .filter(MeasurementRequest.request_id == request_id)
        .first()
    )

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Measurement request not found.",
        )

    if request.status in ["pending", "claimed", "ready", "measuring"]:
        created = normalize_datetime(request.created_at)

        if utc_now() - created > REQUEST_TIMEOUT:
            request.status = "expired"
            db.commit()

    reading = (
        db.query(SensorReading)
        .filter(SensorReading.reading_id == request_id)
        .first()
    )

    return {
        "status": request.status,
        "request_id": request.request_id,
        "bin_id": request.bin_code,
        "reading_id": reading.reading_id if reading else None,
        "weight_g": reading.weight_g if reading else None,
        "created_at": request.created_at.isoformat(),
    }


# ------------------------------------------------------------
# EXISTING ENDPOINT: DIRECT WEIGHT UPLOAD
# POST /api/sensor/weight
# ------------------------------------------------------------

@router.post("/weight")
def receive_weight(
    payload: WeightReadingRequest,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, payload.bin_id)

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
            "consumed": existing.consumed,
        }

    reading = SensorReading(
        bin_code=payload.bin_id,
        sensor_id=payload.sensor_id,
        reading_id=payload.reading_id,
        weight_g=payload.weight_g,
        consumed=False,
        created_at=utc_now(),
    )

    db.add(reading)
    db.commit()
    db.refresh(reading)

    return {
        "status": "received",
        "reading_id": reading.reading_id,
        "bin_id": reading.bin_code,
        "weight_g": reading.weight_g,
        "consumed": reading.consumed,
        "created_at": reading.created_at.isoformat(),
    }


# ------------------------------------------------------------
# EXISTING ENDPOINT: LATEST UNUSED READING
# GET /api/sensor/weight/latest/{bin_id}
# ------------------------------------------------------------

@router.get("/weight/latest/{bin_id}")
def get_latest_weight(
    bin_id: str,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, bin_id)

    reading = (
        db.query(SensorReading)
        .filter(
            SensorReading.bin_code == bin_id,
            SensorReading.consumed.is_(False),
        )
        .order_by(SensorReading.id.desc())
        .first()
    )

    if not reading:
        return {
            "status": "waiting",
            "bin_id": bin_id,
            "weight_g": None,
            "reading_id": None,
            "message": "No unused sensor reading is available.",
        }

    return {
        "status": "received",
        "bin_id": reading.bin_code,
        "sensor_id": reading.sensor_id,
        "reading_id": reading.reading_id,
        "weight_g": reading.weight_g,
        "consumed": reading.consumed,
        "created_at": reading.created_at.isoformat(),
    }


# ------------------------------------------------------------
# 5. ESP32: CLAIM THE NEXT SEGREGATION COMMAND
# GET /api/sensor/segregation/next?bin_id=BIN001
# ------------------------------------------------------------

@router.get("/segregation/next")
def get_next_segregation_command(
    bin_id: str,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, bin_id)

    command = (
        db.query(SegregationCommand)
        .filter(
            SegregationCommand.bin_code == bin_id,
            SegregationCommand.status == "pending",
        )
        .order_by(SegregationCommand.id.asc())
        .first()
    )

    if not command:
        return {
            "status": "waiting",
            "command_id": None,
            "bin_id": bin_id,
        }

    # Atomically claim the command so repeated polls do not
    # hand the same pending command to multiple requests.
    claimed_count = (
        db.query(SegregationCommand)
        .filter(
            SegregationCommand.id == command.id,
            SegregationCommand.status == "pending",
        )
        .update(
            {
                SegregationCommand.status: "processing",
                SegregationCommand.claimed_at: utc_now(),
            },
            synchronize_session=False,
        )
    )

    db.commit()

    if claimed_count != 1:
        return {
            "status": "waiting",
            "command_id": None,
            "bin_id": bin_id,
        }

    return {
        "status": "claimed",
        "command_id": command.command_id,
        "bin_id": command.bin_code,
        "route_signal": command.route_signal,
    }


# ------------------------------------------------------------
# 6. ESP32: ACKNOWLEDGE COMPLETED SERVO MOVEMENT
# POST /api/sensor/segregation/{command_id}/complete
# ------------------------------------------------------------

@router.post("/segregation/{command_id}/complete")
def complete_segregation_command(
    command_id: str,
    payload: SegregationCompletionBody,
    db: Session = Depends(get_db),
):
    command = (
        db.query(SegregationCommand)
        .filter(
            SegregationCommand.command_id == command_id,
        )
        .first()
    )

    if not command:
        raise HTTPException(
            status_code=404,
            detail="Segregation command not found.",
        )

    # Allow a repeated acknowledgement without repeating movement.
    if command.status == "completed":
        return {
            "status": "completed",
            "command_id": command.command_id,
        }

    if command.status != "processing":
        raise HTTPException(
            status_code=409,
            detail=(
                "Command cannot be completed from status: "
                f"{command.status}"
            ),
        )

    command.status = "completed"
    command.completed_at = utc_now()
    db.commit()

    return {
        "status": "completed",
        "command_id": command.command_id,
    }
# ------------------------------------------------------------
# 7. DASHBOARD: RELEASE COMMAND AFTER TRAY PLACEMENT
# POST /api/sensor/segregation/{command_id}/release
# ------------------------------------------------------------

@router.post("/segregation/{command_id}/release")
def release_segregation_command(
    command_id: str,
    payload: SegregationPlacementBody,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, payload.bin_id)

    command = (
        db.query(SegregationCommand)
        .filter(SegregationCommand.command_id == command_id)
        .first()
    )

    if not command:
        raise HTTPException(status_code=404, detail="Segregation command not found.")

    if command.bin_code != payload.bin_id:
        raise HTTPException(
            status_code=403,
            detail="This command does not belong to the specified bin.",
        )

    # Safe retry: a repeated click must not create or release a second command.
    if command.status == "pending":
        return {
            "status": "released",
            "command_id": command.command_id,
            "bin_id": command.bin_code,
            "route_signal": command.route_signal,
        }

    if command.status != "awaiting_placement":
        raise HTTPException(
            status_code=409,
            detail=f"Command cannot be released from status: {command.status}",
        )

    command.status = "pending"
    db.commit()

    return {
        "status": "released",
        "command_id": command.command_id,
        "bin_id": command.bin_code,
        "route_signal": command.route_signal,
    }


# ------------------------------------------------------------
# 8. DASHBOARD: CHECK PHYSICAL SEGREGATION STATUS
# GET /api/sensor/segregation/{command_id}/status?bin_id=BIN001
# ------------------------------------------------------------

@router.get("/segregation/{command_id}/status")
def get_segregation_status(
    command_id: str,
    bin_id: str,
    db: Session = Depends(get_db),
):
    validate_active_bin(db, bin_id)

    command = (
        db.query(SegregationCommand)
        .filter(SegregationCommand.command_id == command_id)
        .first()
    )

    if not command:
        raise HTTPException(status_code=404, detail="Segregation command not found.")

    if command.bin_code != bin_id:
        raise HTTPException(
            status_code=403,
            detail="This command does not belong to the specified bin.",
        )

    return {
        "status": command.status,
        "command_id": command.command_id,
        "bin_id": command.bin_code,
        "route_signal": command.route_signal,
    }
