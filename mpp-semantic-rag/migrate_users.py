from app.database.database import SessionLocal
from app.database.models import User
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


# Existing users from the old localStorage system.
#
# IMPORTANT:
# Alex Rivera did not have a password stored in localStorage.
# Replace "CHANGE_THIS_PASSWORD" with a new password of your choice.
users_to_migrate = [
    {
        "full_name": "Alex Johnson",
        "username": "alex_john",
        "password": "1234",
        "wallet_address": "0xC0ca187306FD925346803aCCFa82ca8fd722460E",
    },
    {
        "full_name": "Alex Rivera",
        "username": "alex_rivera",
        "password": "riv1234",
        "wallet_address": "0x2f45eF660233ebD3fE2ff5370fC41A1477f5f400",
    },
]


db = SessionLocal()

try:
    for data in users_to_migrate:

        # Check whether this wallet already exists.
        existing = (
            db.query(User)
            .filter(
                User.wallet_address.ilike(
                    data["wallet_address"]
                )
            )
            .first()
        )

        if existing:
            print(
                f"User already exists: "
                f"{existing.username} "
                f"({existing.wallet_address})"
            )
            continue

        # Check whether username already exists.
        existing_username = (
            db.query(User)
            .filter(
                User.username.ilike(
                    data["username"]
                )
            )
            .first()
        )

        if existing_username:
            print(
                f"Username already exists: "
                f"{existing_username.username}"
            )
            continue

        # Generate a secure password hash.
        hashed_password = password_hash.hash(
            data["password"]
        )

        # Create database user.
        user = User(
            full_name=data["full_name"],
            username=data["username"],
            password_hash=hashed_password,
            wallet_address=data["wallet_address"],
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(
            f"Created user: "
            f"{user.username} "
            f"({user.wallet_address})"
        )

finally:
    db.close()
