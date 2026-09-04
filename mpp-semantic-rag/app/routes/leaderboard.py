from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.database import get_db
from app.database.models import Deposit

router = APIRouter()


@router.get("")
def get_leaderboard(
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            Deposit.wallet_address,
            func.sum(Deposit.weight_g).label("total_weight_g"),
            func.sum(Deposit.reward_amount).label("total_tokens"),
            func.count(Deposit.id).label("deposit_count"),
        )
        .group_by(Deposit.wallet_address)
        .order_by(func.sum(Deposit.reward_amount).desc())
        .all()
    )

    return [
        {
            "wallet_address": wallet_address,
            "total_weight_g": float(total_weight_g or 0),
            "total_tokens": float(total_tokens or 0),
            "deposit_count": int(deposit_count or 0),
        }
        for (
            wallet_address,
            total_weight_g,
            total_tokens,
            deposit_count,
        ) in results
    ]
