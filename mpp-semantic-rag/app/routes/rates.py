import json
from pathlib import Path

from fastapi import APIRouter, HTTPException


router = APIRouter()

# Resolve relative to this file, not the process working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_FILE = PROJECT_ROOT / "data" / "rate_history.json"


def _read_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Rate history is currently unreadable.",
        ) from exc

    if not isinstance(data, list) or any(
        not isinstance(row, dict) for row in data
    ):
        raise HTTPException(
            status_code=503,
            detail="Rate history has an invalid format.",
        )

    return data


@router.get("")
def get_latest_rates():
    """Return the latest saved snapshot for each material; never fetch rates."""
    history = _read_history()
    latest_by_material = {}

    # Choose the newest timestamp per material, regardless of file order.
    for index, row in enumerate(history):
        key = row.get("material_key")
        if not key:
            continue

        timestamp = str(row.get("fetched_at", ""))
        previous = latest_by_material.get(key)

        if previous is None or (
            timestamp,
            index,
        ) > (
            str(previous.get("fetched_at", "")),
            previous["_history_index"],
        ):
            latest_by_material[key] = {
                **row,
                "_history_index": index,
            }

    # Remove the internal ordering field from API output.
    latest_by_material = {
        key: {
            field: value
            for field, value in row.items()
            if field != "_history_index"
        }
        for key, row in latest_by_material.items()
    }

    rates = sorted(
        latest_by_material.values(),
        key=lambda row: str(row.get("item", "")).casefold(),
    )

    return {
        "source": "saved_rate_history",
        "read_only": True,
        "count": len(rates),
        "rates": rates,
    }


@router.get("/history")
def get_rate_history():
    """Return all saved snapshots, newest first."""
    history = _read_history()

    ordered = sorted(
        history,
        key=lambda row: str(row.get("fetched_at", "")),
        reverse=True,
    )

    return {
        "source": "saved_rate_history",
        "read_only": True,
        "count": len(ordered),
        "history": ordered,
    }
