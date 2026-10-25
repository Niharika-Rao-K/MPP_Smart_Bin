import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


# Deliberately accept only explicit currency + per-kilogram formats.
# A bare number, a price range, or a generic number is not a verified rate.
_RATE_PATTERNS = (
    re.compile(
        r"(?:₹|INR\s*|Rs\.?\s*)\s*"
        r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
        r"\s*(?:/|per\s+)\s*kg\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
        r"\s*(?:INR|Rs\.?)\s*(?:/|per\s+)\s*kg\b",
        re.IGNORECASE,
    ),
)


def extract_rate_inr_per_kg(text: str) -> float | None:
    """Return a rate only when exactly one distinct explicit rate is found."""
    if not isinstance(text, str) or not text.strip():
        return None

    matches = []
    for pattern in _RATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                value = float(match.group(1).replace(",", ""))
            except (TypeError, ValueError):
                continue
            if value > 0:
                matches.append(value)

    distinct = set(matches)
    if len(distinct) != 1:
        return None

    return round(distinct.pop(), 4)


def _load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Cannot safely read rate history at {path}; no changes made."
        ) from exc

    if not isinstance(data, list) or any(
        not isinstance(row, dict) for row in data
    ):
        raise ValueError(
            f"Rate history at {path} must be a JSON list of records."
        )

    return data


def refresh_rate_snapshots(
    profiles: list[dict],
    history_path: str | Path,
    fetcher: Callable[[str], dict],
    now: str | None = None,
) -> list[dict]:
    """
    Record source observations without modifying profiles or reward policy.

    On extraction failure:
    - preserve the most recent successfully observed rate, if any;
    - otherwise expose the configured profile rate as an unverified baseline;
    - mark the snapshot stale/unverified rather than current.

    The caller supplies the fetcher, allowing tests to avoid network access.
    """
    path = Path(history_path)
    history = _load_history(path)
    timestamp = now or datetime.now(timezone.utc).isoformat()

    # Stable material key: the normalized item name, not a missing profile ID.
    def material_key(profile: dict) -> str:
        item = str(profile.get("item", "")).strip().casefold()
        if not item:
            raise ValueError("Every rate profile must have a non-empty item.")
        return item

    # Fetch each unique URL at most once during this refresh.
    source_results = {}
    snapshots = []

    for profile in profiles:
        key = material_key(profile)
        url = str(profile.get("rate_source_url") or "").strip()

        if url not in source_results:
            if not url:
                source_results[url] = {
                    "status": "not_configured",
                    "source_url": "",
                    "text_excerpt": "",
                }
            else:
                try:
                    result = fetcher(url)
                    source_results[url] = (
                        result if isinstance(result, dict) else {
                            "status": "invalid_fetch_result",
                            "source_url": url,
                            "text_excerpt": "",
                        }
                    )
                except Exception as exc:
                    # Do not let a source outage crash the whole refresh.
                    source_results[url] = {
                        "status": "unavailable",
                        "source_url": url,
                        "text_excerpt": "",
                        "error_type": type(exc).__name__,
                    }

        source_result = source_results[url]
        extracted = extract_rate_inr_per_kg(
            source_result.get("text_excerpt", "")
        )
        fetch_status = str(source_result.get("status", "unknown"))

        # Find the most recent successfully extracted rate for this material.
        previous = next(
            (
                row for row in reversed(history)
                if row.get("material_key") == key
                and row.get("observed_rate_inr_per_kg") is not None
                and row.get("status") in {"CURRENT", "OBSERVED", "CACHED"}
            ),
            None,
        )

        configured_rate = profile.get("rate_inr_per_kg")
        try:
            configured_rate = float(configured_rate)
            if configured_rate <= 0:
                configured_rate = None
        except (TypeError, ValueError):
            configured_rate = None

        if extracted is not None and fetch_status == "fetched":
            status = "OBSERVED"
            last_known = extracted
            observed_rate = extracted
        elif extracted is not None and fetch_status == "cached":
            status = "CACHED"
            last_known = extracted
            observed_rate = extracted
        elif previous is not None:
            status = "STALE"
            last_known = previous["observed_rate_inr_per_kg"]
            observed_rate = None
        elif configured_rate is not None:
            status = "BASELINE_UNVERIFIED"
            last_known = configured_rate
            observed_rate = None
        else:
            status = "NO_RATE"
            last_known = None
            observed_rate = None

        snapshot = {
            "material_key": key,
            "item": str(profile["item"]),
            "source_url": url or None,
            "fetched_at": timestamp,
            "fetch_status": fetch_status,
            "status": status,
            "observed_rate_inr_per_kg": observed_rate,
            "last_known_rate_inr_per_kg": last_known,
            "configured_baseline_inr_per_kg": configured_rate,
            "rate_unit": "INR/kg",
        }

        history.append(snapshot)
        snapshots.append(snapshot)

    # Persist the complete history; replace atomically to avoid partial JSON.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)

    return snapshots
