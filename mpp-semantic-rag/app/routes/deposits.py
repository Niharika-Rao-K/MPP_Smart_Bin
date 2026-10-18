from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Deposit


router = APIRouter()


@router.get("/{wallet_address}")
def get_deposits(
    wallet_address: str,
    db: Session = Depends(get_db),
):
    deposits = (
        db.query(Deposit)
        .filter(
            Deposit.wallet_address == wallet_address
        )
        .order_by(
            Deposit.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": deposit.id,
            "transaction_id": deposit.transaction_id,
            "bin_id": deposit.bin_id,
            "wallet_address": deposit.wallet_address,
            "predicted_label": deposit.predicted_label,
            "confidence": deposit.confidence,
            "weight_g": deposit.weight_g,
            "decision": deposit.decision,
            "hardware_route_signal": deposit.hardware_route_signal,
            "reward_amount": deposit.reward_amount,
            "reward_status": deposit.reward_status,
            "tx_hash": deposit.tx_hash,
            "created_at": (
                deposit.created_at.isoformat()
                if deposit.created_at
                else None
            ),
        }
        for deposit in deposits
    ]
