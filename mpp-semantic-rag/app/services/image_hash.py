import hashlib
import io
import warnings
from datetime import datetime, timedelta, timezone

import imagehash
from PIL import Image, ImageOps, UnidentifiedImageError


# These thresholds are provisional. Do not use them to reject deposits
# until they have been evaluated against representative real photographs.
DUP_T = 6
SUSPECT_T = 10
WINDOW_DAYS = 30

# Prevent unusually large decoded images from consuming excessive memory.
MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidImageError(ValueError):
    """Raised when uploaded bytes are not a supported, safe image."""


def _load(data: bytes) -> Image.Image:
    if not isinstance(data, bytes) or not data:
        raise InvalidImageError("Image data is empty or invalid.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            source = Image.open(io.BytesIO(data))

            if source.format not in ALLOWED_FORMATS:
                raise InvalidImageError("Unsupported image format.")

            width, height = source.size
            if width <= 0 or height <= 0:
                raise InvalidImageError("Invalid image dimensions.")

            if width * height > MAX_IMAGE_PIXELS:
                raise InvalidImageError("Image dimensions are too large.")

            source.verify()

            # verify() invalidates the opened image, so reopen the bytes.
            source = Image.open(io.BytesIO(data))

            if source.format not in ALLOWED_FORMATS:
                raise InvalidImageError("Unsupported image format.")

            width, height = source.size
            if width * height > MAX_IMAGE_PIXELS:
                raise InvalidImageError("Image dimensions are too large.")

            return ImageOps.exif_transpose(source).convert("RGB")

    except InvalidImageError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise InvalidImageError(
            "Uploaded file is not a valid, supported image."
        ) from exc


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
    """Calculate pHash for simple orientation and reflection variants."""
    img = _load(data)

    variants = [
        img,
        ImageOps.mirror(img),
        ImageOps.flip(img),
        img.rotate(90, expand=True),
        img.rotate(180),
        img.rotate(270, expand=True),
    ]

    return [
        str(imagehash.phash(variant, hash_size=8))
        for variant in variants
    ]


def check_duplicate(db, ImageFingerprint, data: bytes) -> dict:
    """
    Compare an image with previously accepted fingerprints.

    Exact SHA-256 matches are checked across all time.
    Perceptual matches are checked within the configured time window.

    Invalid image data raises InvalidImageError.
    Database errors are deliberately not caught here.
    """
    hashes = compute(data)

    # Exact duplicates remain ineligible even after the 30-day window.
    exact = (
        db.query(ImageFingerprint)
        .filter(
            ImageFingerprint.sha256 == hashes["sha256"],
            ImageFingerprint.status == "accepted",
        )
        .first()
    )

    if exact:
        return {
            "verdict": "duplicate",
            "match_type": "exact",
            "exact_match": True,
            "distance": 0,
            "hashes": hashes,
        }

    # Perceptual comparisons use only recent accepted fingerprints.
    since = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)

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
        if row.phash:
            best = min(
                best,
                min(hamming(variant, row.phash) for variant in variants),
            )

    if best <= DUP_T:
        verdict = "duplicate"
    elif best <= SUSPECT_T:
        verdict = "suspicious"
    else:
        verdict = "ok"

    return {
        "verdict": verdict,
        "match_type": "perceptual" if best <= SUSPECT_T else "none",
        "exact_match": False,
        "distance": best,
        "hashes": hashes,
    }