from app.database.database import SessionLocal
from app.database.models import User
from passlib.context import CryptContext


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


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
        existing = (
            db.query(User)
            .filter(User.wallet_address.ilike(data["wallet_address"]))
            .first()
        )

        if existing:
            print(
                f"User already exists: "
                f"{existing.username} ({existing.wallet_address})"
            )
            continue

        user = User(
            full_name=data["full_name"],
            username=data["username"],
            password_hash=pwd_context.hash(data["password"]),
            wallet_address=data["wallet_address"],
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"Created user: {user.username}")

finally:
    db.close()
