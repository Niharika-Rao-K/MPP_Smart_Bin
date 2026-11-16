import hashlib
import io
from datetime import datetime, timedelta, timezone

import imagehash
from PIL import Image, ImageOps

DUP_T = 6          # distance <= 6  -> duplicate
SUSPECT_T = 10     # distance <= 12 -> too similar
WINDOW_DAYS = 30


def _load(data: bytes) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def compute(data: bytes) -> dict:
    img = _load(data)
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "phash": str(imagehash.phash(img, hash_size=8)),
        "dhash": str(imagehash.dhash(img, hash_size=8)),
    }


def variant_phashes(data: bytes) -> list:
    """pHash of the image plus flipped/rotated copies (catches simple edits)."""
    img = _load(data)
    variants = [
        img,
        ImageOps.mirror(img),
        ImageOps.flip(img),
        img.rotate(90, expand=True),
        img.rotate(180),
        img.rotate(270, expand=True),
    ]
    return [str(imagehash.phash(v, hash_size=8)) for v in variants]


def check_duplicate(db, ImageFingerprint, data: bytes) -> dict:
    hashes = compute(data)

    exact = (
        db.query(ImageFingerprint)
        .filter(
            ImageFingerprint.sha256 == hashes["sha256"],
            ImageFingerprint.status == "accepted",
        )
        .first()
    )
    if exact:
        return {"verdict": "duplicate", "distance": 0, "hashes": hashes}

    since = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).replace(tzinfo=None)
    rows = (
        db.query(ImageFingerprint)
        .filter(
            ImageFingerprint.created_at >= since,
            ImageFingerprint.status == "accepted",
        )
        .all()
    )

    variants = variant_phashes(data)
    best = 64
    for row in rows:
        best = min(best, min(hamming(v, row.phash) for v in variants))

    if best <= DUP_T:
        verdict = "duplicate"
    elif best <= SUSPECT_T:
        verdict = "suspicious"
    else:
        verdict = "ok"

    return {"verdict": verdict, "distance": best, "hashes": hashes}