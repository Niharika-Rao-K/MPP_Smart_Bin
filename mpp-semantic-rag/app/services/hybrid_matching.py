from typing import Any

from app.services.rag_client import LABEL_ALIASES, PROFILE_BY_ID, _normalize_label
from app.services.semantic_retrieval import retrieve_semantic_profiles


# Experimental values only. Calibrate with a labelled evaluation dataset.
MAX_SEMANTIC_DISTANCE = 1.45
MIN_TOP_TWO_DISTANCE_GAP = 0.10


def match_material(query: str) -> dict[str, Any]:
    """
    Resolve a label by exact alias first, then semantic retrieval.

    This function proposes a material profile. It does not verify purity,
    brand authenticity, or reward eligibility.
    """
    if not isinstance(query, str) or not query.strip():
        return {
            "status": "REJECTED",
            "match_method": "none",
            "reason": "empty_query",
            "candidate": None,
        }

    normalized = _normalize_label(query)

    # Exact aliases take precedence over semantic similarity.
    profile_key = LABEL_ALIASES.get(normalized)

    if profile_key:
        profile = PROFILE_BY_ID.get(profile_key)

        if profile is not None:
            return {
                "status": "CANDIDATE_FOUND",
                "match_method": "exact_alias",
                "reason": "known_label_alias",
                "candidate": {
                    "profile_id": profile_key,
                    "item": profile.get("item"),
                    "category": profile.get("category"),
                    "material": profile.get("material"),
                    "rate_status": profile.get("rate_status"),
                },
                "brand_verified": False,
                "purity_verified": False,
            }

    candidates = retrieve_semantic_profiles(query, n_results=3)

    if not candidates:
        return {
            "status": "REVIEW_REQUIRED",
            "match_method": "semantic",
            "reason": "no_candidates",
            "candidate": None,
        }

    best = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    best_distance = best["distance"]

    gap = (
        second["distance"] - best_distance
        if second is not None
        else None
    )

    if best_distance > MAX_SEMANTIC_DISTANCE:
        return {
            "status": "REVIEW_REQUIRED",
            "match_method": "semantic",
            "reason": "best_candidate_too_distant",
            "candidate": best,
            "distance": best_distance,
            "second_best_gap": gap,
            "brand_verified": False,
            "purity_verified": False,
        }

    if gap is not None and gap < MIN_TOP_TWO_DISTANCE_GAP:
        return {
            "status": "REVIEW_REQUIRED",
            "match_method": "semantic",
            "reason": "ambiguous_candidates",
            "candidate": best,
            "distance": best_distance,
            "second_best_gap": gap,
            "brand_verified": False,
            "purity_verified": False,
        }

    return {
        "status": "CANDIDATE_FOUND",
        "match_method": "semantic",
        "reason": "candidate_passed_experimental_thresholds",
        "candidate": best,
        "distance": best_distance,
        "second_best_gap": gap,
        "brand_verified": False,
        "purity_verified": False,
    }
