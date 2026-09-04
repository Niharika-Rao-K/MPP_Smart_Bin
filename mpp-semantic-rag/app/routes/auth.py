from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User

from passlib.context import CryptContext


router = APIRouter()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


class RegisterRequest(BaseModel):
    full_name: str
    username: str
    password: str
    wallet_address: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register_user(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    username = request.username.strip()
    wallet_address = request.wallet_address.strip()

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required.",
        )

    if len(request.password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 4 characters.",
        )

    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address.",
        )

    existing_username = (
        db.query(User)
        .filter(User.username.ilike(username))
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=409,
            detail="That username is already registered.",
        )

    existing_wallet = (
        db.query(User)
        .filter(
            User.wallet_address.ilike(wallet_address)
        )
        .first()
    )

    if existing_wallet:
        raise HTTPException(
            status_code=409,
            detail="That wallet address is already registered.",
        )

    password_hash = pwd_context.hash(request.password)

    user = User(
        full_name=request.full_name.strip(),
        username=username,
        password_hash=password_hash,
        wallet_address=wallet_address,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "status": "SUCCESS",
        "message": "User registered successfully.",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "wallet_address": user.wallet_address,
        },
    }


@router.post("/login")
def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    username = request.username.strip()

    user = (
        db.query(User)
        .filter(User.username.ilike(username))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    if not pwd_context.verify(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    return {
        "status": "SUCCESS",
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "wallet_address": user.wallet_address,
        },
    }
