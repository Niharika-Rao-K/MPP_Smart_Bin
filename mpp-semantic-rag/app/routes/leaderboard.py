from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.database import get_db
from app.database.models import Deposit, User

router = APIRouter()


@router.get("")
def get_leaderboard(
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            User.username,
            Deposit.wallet_address,
            func.sum(Deposit.weight_g).label("total_weight_g"),
            func.sum(Deposit.reward_amount).label("total_tokens"),
            func.count(Deposit.id).label("deposit_count"),
        )
        .join(
            User,
            User.wallet_address == Deposit.wallet_address,
        )
        .filter(
            Deposit.decision == "VERIFIED_CLEAN"
        )
        .group_by(
            User.username,
            Deposit.wallet_address,
        )
        .order_by(
            func.sum(Deposit.reward_amount).desc(),
            func.sum(Deposit.weight_g).desc(),
        )
        .all()
    )

    return [
        {
            "username": username,
            "wallet_address": wallet_address,
            "total_weight_g": float(total_weight_g or 0),
            "total_tokens": float(total_tokens or 0),
            "deposit_count": int(deposit_count or 0),
        }
        for (
            username,
            wallet_address,
            total_weight_g,
            total_tokens,
            deposit_count,
        ) in results
    ]
