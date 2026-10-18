from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Bin


router = APIRouter()


@router.get("/{bin_code}")
def get_bin(
    bin_code: str,
    db: Session = Depends(get_db),
):
    bin_record = (
        db.query(Bin)
        .filter(Bin.bin_code == bin_code)
        .first()
    )

    if not bin_record:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown bin: {bin_code}",
        )

    return {
        "id": bin_record.id,
        "bin_code": bin_record.bin_code,
        "location": bin_record.location,
        "status": bin_record.status,
        "active": bin_record.status == "ACTIVE",
    }
