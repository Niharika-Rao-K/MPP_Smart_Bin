from app.database.database import SessionLocal
from app.database.models import Bin


db = SessionLocal()

try:
    existing_bin = (
        db.query(Bin)
        .filter(Bin.bin_code == "BIN001")
        .first()
    )

    if existing_bin:
        print("BIN001 already exists.")
    else:
        bin_record = Bin(
            bin_code="BIN001",
            location="BMSCE Block A",
            status="ACTIVE",
        )

        db.add(bin_record)
        db.commit()
        db.refresh(bin_record)

        print(f"Created bin: {bin_record.bin_code}")

finally:
    db.close()
