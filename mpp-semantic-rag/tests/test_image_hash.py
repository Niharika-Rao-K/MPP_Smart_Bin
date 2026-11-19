import io
import random
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image, ImageDraw, ImageOps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.database.models import ImageFingerprint
from app.services.image_hash import (
    InvalidImageError,
    check_duplicate,
    compute,
)


def make_image(seed, size=(400, 300)):
    rnd = random.Random(seed)
    img = Image.new("RGB", size, (rnd.randint(0, 255),) * 3)
    d = ImageDraw.Draw(img)
    for _ in range(25):
        x0 = rnd.randint(0, size[0] - 60)
        y0 = rnd.randint(0, size[1] - 60)
        d.rectangle(
            [x0, y0, x0 + rnd.randint(20, 150), y0 + rnd.randint(20, 150)],
            fill=tuple(rnd.randint(0, 255) for _ in range(3)),
        )
    return img


def to_bytes(img, fmt="JPEG", quality=90):
    buf = io.BytesIO()
    img.save(buf, fmt, quality=quality)
    return buf.getvalue()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def store(db, data, status="accepted"):
    h = compute(data)
    db.add(ImageFingerprint(
        sha256=h["sha256"], phash=h["phash"], dhash=h["dhash"],
        wallet_address="0x" + "1" * 40, bin_code="BIN001", status=status,
    ))
    db.commit()


def test_new_image_is_ok(db):
    assert check_duplicate(db, ImageFingerprint, to_bytes(make_image(1)))["verdict"] == "ok"


def test_exact_copy_is_duplicate(db):
    data = to_bytes(make_image(1))
    store(db, data)
    result = check_duplicate(db, ImageFingerprint, data)
    assert result["verdict"] == "duplicate" and result["distance"] == 0


def test_resized_recompressed_is_duplicate(db):
    img = make_image(2)
    store(db, to_bytes(img))
    attacked = to_bytes(img.resize((200, 150)), quality=40)
    assert check_duplicate(db, ImageFingerprint, attacked)["verdict"] == "duplicate"


def test_mirrored_is_duplicate(db):
    img = make_image(3)
    store(db, to_bytes(img))
    attacked = to_bytes(ImageOps.mirror(img))
    assert check_duplicate(db, ImageFingerprint, attacked)["verdict"] == "duplicate"


def test_rotated_is_duplicate(db):
    img = make_image(4)
    store(db, to_bytes(img))
    attacked = to_bytes(img.rotate(90, expand=True))
    assert check_duplicate(db, ImageFingerprint, attacked)["verdict"] == "duplicate"


def test_different_image_is_ok(db):
    store(db, to_bytes(make_image(5)))
    assert check_duplicate(db, ImageFingerprint, to_bytes(make_image(99)))["verdict"] == "ok"


def test_rejected_images_are_not_remembered(db):
    data = to_bytes(make_image(6))
    store(db, data, status="rejected")
    assert check_duplicate(db, ImageFingerprint, data)["verdict"] == "ok"


def test_corrupt_image_raises(db):
    with pytest.raises(InvalidImageError):
        check_duplicate(db, ImageFingerprint, b"not an image")

def test_exact_duplicate_is_detected_after_30_days(db):
    data = to_bytes(make_image(10))
    store(db, data)

    old_record = db.query(ImageFingerprint).first()
    old_record.created_at = datetime.now(timezone.utc) - timedelta(days=45)
    db.commit()

    result = check_duplicate(db, ImageFingerprint, data)

    assert result["verdict"] == "duplicate"
    assert result["match_type"] == "exact"
    assert result["exact_match"] is True


def test_perceptual_match_older_than_30_days_is_ignored(db):
    img = make_image(11)
    original = to_bytes(img)
    store(db, original)

    old_record = db.query(ImageFingerprint).first()
    old_record.created_at = datetime.now(timezone.utc) - timedelta(days=45)
    db.commit()

    # Different bytes, but the same visual image.
    recompressed = to_bytes(img, quality=40)
    result = check_duplicate(db, ImageFingerprint, recompressed)

    assert result["exact_match"] is False
    assert result["verdict"] == "ok"
    assert result["match_type"] == "none"


def test_exact_duplicate_result_identifies_match_type(db):
    data = to_bytes(make_image(12))
    store(db, data)

    result = check_duplicate(db, ImageFingerprint, data)

    assert result["match_type"] == "exact"
    assert result["exact_match"] is True
    assert result["distance"] == 0
