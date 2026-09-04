from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from app.database.database import get_db
from app.database.models import User


router = APIRouter()

password_hash = PasswordHash.recommended()


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

    # Validate username
    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required.",
        )

    # Validate password
    if len(request.password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 4 characters.",
        )

    # Validate wallet address
    if (
        not wallet_address.startswith("0x")
        or len(wallet_address) != 42
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address.",
        )

    # Check username
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

    # Check wallet
    existing_wallet = (
        db.query(User)
        .filter(User.wallet_address.ilike(wallet_address))
        .first()
    )

    if existing_wallet:
        raise HTTPException(
            status_code=409,
            detail="That wallet address is already registered.",
        )

    # Hash password before storing it
    hashed_password = password_hash.hash(request.password)

    user = User(
        full_name=request.full_name.strip(),
        username=username,
        password_hash=hashed_password,
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

    # Find user by username
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

    # Verify password against stored hash
    if not password_hash.verify(
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
