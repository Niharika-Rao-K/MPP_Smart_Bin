from app.services.hybrid_matching import match_material
from app.services.material_validation import validate_material_candidate
from app.services.rag_client import PROFILE_BY_ID


def evaluate_with_hybrid_rag(label: str, real_weight_g: float) -> dict:
    """
    Experimental hybrid evaluator.

    This module is isolated from the live deposit flow.
    Semantic similarity proposes candidates; it does not prove purity,
    brand identity, or eligibility for automatic rewards.
    """
    base = {
        "matched_profile_id": None,
        "matched_item": None,
        "category": None,
        "material": None,
        "match_type": "none",
        "match_distance": None,
        "similarity_score": None,
        "target_weight_g": None,
        "margin_g": None,
        "weight_difference_g": None,
        "rate_inr_per_kg": 0.0,
        "metadata": {},
    }

    def reject(status: str, action: str, **extra) -> dict:
        result = {**base, **extra}
        result["final_decision"] = {
            "status": status,
            "action": action,
            "hardware_route_signal": "R",
            "reward_eligible": False,
        }
        return result

    if not isinstance(label, str) or not label.strip():
        return reject("UNRECOGNIZED", "No visual label was detected.")

    try:
        weight = float(real_weight_g)
    except (TypeError, ValueError):
        return reject("REJECTED", "Invalid weight reading.")

    if weight <= 0:
        return reject("REJECTED", "Invalid weight reading.")

    try:
        match = match_material(label)
    except Exception:
        # Fail closed. Do not expose internal exception details.
        return reject(
            "RAG_ERROR",
            "Material retrieval failed. No reward is authorized.",
        )

    if match.get("status") != "CANDIDATE_FOUND":
        return reject(
            match.get("status", "REVIEW_REQUIRED"),
            "No unambiguous material candidate was established.",
            match_type=match.get("match_method", "none"),
            match_distance=match.get("distance"),
        )

    candidate = match.get("candidate") or {}
    profile_id = candidate.get("profile_id")
    profile = PROFILE_BY_ID.get(profile_id)

    if not isinstance(profile, dict):
        return reject(
            "REVIEW_REQUIRED",
            "Candidate profile is missing from canonical knowledge data.",
            match_type=match.get("match_method", "none"),
            match_distance=match.get("distance"),
        )

    try:
        validation = validate_material_candidate(profile, weight)
    except (TypeError, ValueError, KeyError):
        return reject(
            "RAG_ERROR",
            "Material profile validation failed. No reward is authorized.",
            matched_profile_id=profile_id,
            matched_item=profile.get("item"),
            metadata=dict(profile),
            match_type=match.get("match_method", "none"),
            match_distance=match.get("distance"),
        )

    target = float(profile["typical_empty_weight_g"])
    tolerance = float(profile["weight_tolerance_percent"])
    margin = target * tolerance / 100.0
    difference = abs(weight - target)

    category = str(profile.get("category", "")).lower()
    if "metal" in category:
        route = "M"
    elif "plastic" in category:
        route = "P"
    elif "e-waste" in category or "ewaste" in category:
        route = "E"
    else:
        route = "R"

    rate_status = str(profile.get("rate_status", "")).lower()
    recyclable = bool(profile.get("recyclable", False))

    # Only the explicitly approved reference status can qualify.
    # Weight compatibility does not prove purity or exact brand.
    reward_eligible = (
        match.get("match_method") == "exact_alias"
        and validation["status"] == "WEIGHT_COMPATIBLE"
        and validation.get("weight_compatible") is True
        and validation.get("automatic_rate_eligible") is True
        and recyclable
        and route in {"P", "M", "E"}
    )

    if validation["status"] == "WEIGHT_MISMATCH":
        status = "WEIGHT_MISMATCH"
        action = "Measured weight is outside the candidate profile range."
    elif validation["status"] == "RATE_REVIEW_REQUIRED":
        status = "RATE_REVIEW_REQUIRED"
        action = "Rate provenance requires review before automatic rewards."
    elif not recyclable or route == "R":
        status = "REVIEW_REQUIRED"
        action = "Material routing or recyclability needs review."
    elif match.get("match_method") == "semantic":
        status = "REVIEW_REQUIRED"
        action = "Semantic candidate requires review; it cannot authorize automatic rewards."
    elif reward_eligible:
        status = "WEIGHT_COMPATIBLE"
        action = "Exact alias passed weight and approved-rate policy checks."
    else:
        status = "REVIEW_REQUIRED"
        action = "Candidate is not eligible for automatic rewards."

    metadata = dict(profile)
    metadata["validation"] = validation
    metadata["brand_verified"] = False
    metadata["purity_verified"] = False

    return {
        **base,
        "matched_profile_id": profile_id,
        "matched_item": profile.get("item"),
        "category": profile.get("category"),
        "material": profile.get("material"),
        "match_type": match.get("match_method", "none"),
        "match_distance": match.get("distance"),
        "similarity_score": None,
        "target_weight_g": target,
        "margin_g": round(margin, 2),
        "weight_difference_g": round(difference, 2),
        "rate_inr_per_kg": float(profile.get("rate_inr_per_kg", 0) or 0),
        "metadata": metadata,
        "final_decision": {
            "status": status,
            "action": action,
            "hardware_route_signal": route if reward_eligible else "R",
            "reward_eligible": reward_eligible,
        },
    }
