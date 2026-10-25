from typing import Any


# Only this status is eligible under the initial automatic-rate policy.
# This policy must be reviewed before integration with reward calculation.
AUTOMATIC_RATE_STATUSES = {"reference"}


def validate_material_candidate(
    profile: dict[str, Any],
    measured_weight_g: float,
) -> dict[str, Any]:
    """
    Evaluate weight compatibility and rate provenance.

    Does not establish purity, exact brand identity, or actual recyclability.
    Does not calculate or issue a reward.
    """
    if not isinstance(profile, dict):
        raise TypeError("profile must be a dictionary")

    try:
        weight = float(measured_weight_g)
        target = float(profile["typical_empty_weight_g"])
        tolerance = float(profile["weight_tolerance_percent"])
        rate = float(profile["rate_inr_per_kg"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "Profile must contain numeric typical weight, tolerance, "
            "and rate fields."
        ) from exc

    if weight <= 0:
        return {
            "status": "REJECTED",
            "reason": "non_positive_weight",
            "weight_compatible": False,
            "rate_status": profile.get("rate_status"),
            "automatic_rate_eligible": False,
            "purity_verified": False,
        }

    if target <= 0 or tolerance < 0 or rate < 0:
        raise ValueError(
            "Profile weight, tolerance, and rate values are invalid."
        )

    margin = target * tolerance / 100.0
    lower = max(0.0, target - margin)
    upper = target + margin
    compatible = lower <= weight <= upper

    rate_status = str(
        profile.get("rate_status", "unknown")
    ).strip().lower()

    automatic_rate_eligible = (
        rate_status in AUTOMATIC_RATE_STATUSES and rate > 0
    )

    if not compatible:
        status = "WEIGHT_MISMATCH"
        reason = "measured_weight_outside_profile_range"
    elif not automatic_rate_eligible:
        status = "RATE_REVIEW_REQUIRED"
        reason = "rate_not_approved_for_automatic_rewards"
    else:
        status = "WEIGHT_COMPATIBLE"
        reason = "weight_in_profile_range"

    return {
        "status": status,
        "reason": reason,
        "measured_weight_g": weight,
        "expected_weight_range_g": [lower, upper],
        "weight_compatible": compatible,
        "rate_inr_per_kg": rate,
        "rate_status": rate_status,
        "automatic_rate_eligible": automatic_rate_eligible,
        "purity_verified": False,
        "brand_verified": False,
    }
