import json
import math
from pathlib import Path
from typing import Any


KNOWLEDGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "waste_knowledge.json"
)

SUPPORTED_LABELS = {
    "diet_coke": "Metal",
    "dairy_milk_wrapper": "Plastic",
    "ram_stick": "E-Waste",
}

FEATURE_NAMES = (
    "peak_g",
    "early_rms_g",
    "area_g_seconds",
    "stable_weight_g",
)

CAPTURE_WINDOW_MS = 2500


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _load_reference(image_label: str) -> dict | None:
    with KNOWLEDGE_PATH.open("r", encoding="utf-8-sig") as file:
        profiles = json.load(file)

    if not isinstance(profiles, list):
        raise ValueError("waste_knowledge.json must contain a list.")

    for profile in profiles:
        if profile.get("classifier_label") == image_label:
            return profile.get("mechanical_reference")

    return None


def _extract_features(
    *,
    stable_weight_g: Any,
    baseline_mean_g: Any,
    raw_samples: Any,
    impact_sample_count: Any,
) -> dict:
    if not _finite_number(stable_weight_g) or float(stable_weight_g) <= 0:
        raise ValueError("Stable weight is missing or invalid.")

    if not _finite_number(baseline_mean_g):
        raise ValueError("Baseline mean is missing or invalid.")

    if (
        not _finite_number(impact_sample_count)
        or float(impact_sample_count) <= 0
        or not float(impact_sample_count).is_integer()
    ):
        raise ValueError("Impact sample count is missing or invalid.")

    if not isinstance(raw_samples, list):
        raise ValueError("Raw impact samples are missing.")

    if len(raw_samples) < 10 or len(raw_samples) != int(impact_sample_count):
        raise ValueError("Insufficient or inconsistent raw impact samples.")

    baseline = float(baseline_mean_g)
    samples = []

    for sample in raw_samples:
        if not isinstance(sample, dict):
            raise ValueError("Invalid raw impact sample.")

        t_ms = sample.get("t_ms")
        weight_g = sample.get("weight_g")

        if not _finite_number(t_ms) or not _finite_number(weight_g):
            raise ValueError("Raw impact sample contains invalid values.")

        t_ms = float(t_ms)
        weight_g = float(weight_g)

        if t_ms < 0:
            raise ValueError("Impact sample timestamp cannot be negative.")

        samples.append((t_ms, weight_g - baseline))

    times = [sample[0] for sample in samples]
    deltas = [sample[1] for sample in samples]

    if any(current <= previous for previous, current in zip(times, times[1:])):
        raise ValueError("Impact sample timestamps must be strictly increasing.")

    early = [
        (t_ms, delta)
        for t_ms, delta in zip(times, deltas)
        if t_ms <= CAPTURE_WINDOW_MS
    ]

    if len(early) < 3:
        raise ValueError("Fewer than three samples in the first 2500 ms.")

    peak_index = max(range(len(early)), key=lambda index: early[index][1])
    peak_g = early[peak_index][1]
    peak_time_ms = early[peak_index][0]

    if peak_g < 0:
        raise ValueError("Impact peak is negative.")

    early_rms_g = math.sqrt(
        sum(delta ** 2 for _, delta in early) / len(early)
    )

    post_peak = [
        (t_ms, abs(delta))
        for t_ms, delta in zip(times, deltas)
        if t_ms >= peak_time_ms
    ]

    if len(post_peak) < 3:
        raise ValueError("Insufficient samples after the impact peak.")

    area_g_seconds = sum(
        (
            (post_peak[index - 1][1] + post_peak[index][1])
            / 2.0
        )
        * (
            (post_peak[index][0] - post_peak[index - 1][0])
            / 1000.0
        )
        for index in range(1, len(post_peak))
    )

    return {
        "peak_g": peak_g,
        "early_rms_g": early_rms_g,
        "area_g_seconds": area_g_seconds,
        "stable_weight_g": float(stable_weight_g),
    }


def _compare_with_reference(features: dict, reference: dict) -> dict:
    reference_features = reference.get("features")

    if not isinstance(reference_features, dict):
        raise ValueError("Reference does not contain feature statistics.")

    comparisons = {}

    for feature_name in FEATURE_NAMES:
        observed = features[feature_name]
        statistics = reference_features.get(feature_name)

        if not isinstance(statistics, dict):
            raise ValueError(f"Missing reference feature: {feature_name}")

        lower = statistics.get("p05")
        upper = statistics.get("p95")
        median = statistics.get("median")
        mad = statistics.get("mad")

        if not all(
            _finite_number(value)
            for value in (lower, upper, median, mad)
        ):
            raise ValueError(f"Invalid reference statistics: {feature_name}")

        lower = float(lower)
        upper = float(upper)
        median = float(median)
        mad = float(mad)

        if lower > upper or mad < 0:
            raise ValueError(f"Invalid reference range: {feature_name}")

        comparisons[feature_name] = {
            "observed": round(observed, 6),
            "p05": lower,
            "median": median,
            "p95": upper,
            "mad": mad,
            "within_reference_range": lower <= observed <= upper,
        }

    matched_count = sum(
        result["within_reference_range"]
        for result in comparisons.values()
    )

    return {
        "feature_comparisons": comparisons,
        "matched_feature_count": matched_count,
        "total_feature_count": len(FEATURE_NAMES),
        "all_features_within_reference": matched_count == len(FEATURE_NAMES),
    }


def assess_mechanical_fingerprint(
    *,
    image_label: str,
    stable_weight_g: Any,
    impact_peak_g: Any = None,
    impact_settling_ms: Any = None,
    impact_sample_count: Any = None,
    baseline_mean_g: Any = None,
    raw_samples: Any = None,
) -> dict:
    """
    Four-feature, exact-image-label mechanical reference assessment.

    This is SHADOW ONLY. Its result must not control deposit acceptance,
    rewards, or hardware routing until separately validated and enabled.
    """

    normalized_label = str(image_label or "").strip().lower()

    base_result = {
        "model_name": "item_specific_mechanical_reference",
        "model_version": "four_feature_reference_v1",
        "status": None,
        "assessment_mode": "SHADOW_ONLY",
        "image_label": normalized_label,
        "predicted_material_class": None,
        "image_expected_class": SUPPORTED_LABELS.get(normalized_label),
        "mechanical_agreement": None,
        "metal_distance": None,
        "e_waste_distance": None,
        "plastic_distance": None,
        "extracted_features": None,
        "feature_comparisons": None,
        "matched_feature_count": None,
        "total_feature_count": len(FEATURE_NAMES),
    }

    if normalized_label not in SUPPORTED_LABELS:
        return {
            **base_result,
            "status": "NOT_APPLICABLE",
            "reason": "Image label is outside the three available mechanical references.",
        }

    try:
        reference = _load_reference(normalized_label)

        if not isinstance(reference, dict):
            return {
                **base_result,
                "status": "REFERENCE_NOT_FOUND",
                "reason": "No mechanical reference exists for this exact image label.",
            }

        if reference.get("status") != "experimental":
            raise ValueError("Mechanical reference is not marked experimental.")

        features = _extract_features(
            stable_weight_g=stable_weight_g,
            baseline_mean_g=baseline_mean_g,
            raw_samples=raw_samples,
            impact_sample_count=impact_sample_count,
        )

        comparison = _compare_with_reference(features, reference)

        agreement = comparison["all_features_within_reference"]

        return {
            **base_result,
            "status": "SHADOW_ASSESSED",
            "mechanical_agreement": agreement,
            "extracted_features": {
                name: round(value, 6)
                for name, value in features.items()
            },
            "feature_comparisons": comparison["feature_comparisons"],
            "matched_feature_count": comparison["matched_feature_count"],
            "reason": (
                "All four features are within the stored P5-P95 ranges."
                if agreement
                else "One or more features are outside the stored P5-P95 ranges."
            ),
        }

    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        return {
            **base_result,
            "status": "INSUFFICIENT_DATA",
            "reason": str(exc),
        }