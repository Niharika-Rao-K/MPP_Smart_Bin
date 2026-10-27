
import json
import re
from pathlib import Path
from app.services.source_retrieval import fetch_reference_page

# ---------------------------------------------------------
# Load the six waste profiles directly from JSON
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "waste_knowledge.json"


def _normalize_label(value):
    """Normalize a detected label for exact matching."""
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


with KNOWLEDGE_PATH.open("r", encoding="utf-8") as file:
    WASTE_PROFILES = json.load(file)

if not isinstance(WASTE_PROFILES, list) or not WASTE_PROFILES:
    raise ValueError("Waste knowledge JSON must contain a non-empty list.")


def _profile_id(profile):
    """Generate a stable ID from the item's name."""
    return _normalize_label(profile["item"])


PROFILE_BY_ID = {
    _profile_id(profile): profile
    for profile in WASTE_PROFILES
}

# Match known labels to the corresponding profile IDs.
# Generic "can" maps to the first can profile because visual
# detection alone cannot reliably distinguish its brand.
LABEL_ALIASES = {
    # Nine-class model: map each label to its matching profile ID.
    "coca_cola_can": "coca_cola_330ml_aluminum_can",
    "coca_cola_330ml_aluminum_can": "coca_cola_330ml_aluminum_can",
    "diet_coke": "diet_coke_beverage_can",
    "diet_coke_beverage_can": "diet_coke_beverage_can",
    "general_metal": "general_metal_scrap",
    "general_metal_scrap": "general_metal_scrap",
    "pepsi_can": "pepsi_330ml_aluminum_can",
    "pepsi_330ml_aluminum_can": "pepsi_330ml_aluminum_can",
    "red_bull_can": "red_bull_beverage_can",
    "red_bull_beverage_can": "red_bull_beverage_can",
    "general_plastic": "general_plastic_waste",
    "general_plastic_waste": "general_plastic_waste",

    # PET bottles
    "bottle": "500ml_pet_water_bottle",
    "plastic_bottle": "500ml_pet_water_bottle",
    "water_bottle": "500ml_pet_water_bottle",
    "pet_bottle": "500ml_pet_water_bottle",
    "pet_water_bottle": "500ml_pet_water_bottle",
    "500ml_pet_water_bottle": "500ml_pet_water_bottle",

    # Wrappers are categorized as Plastic.
    "snack_wrapper": "snack_wrapper",
    "snickers_wrapper": "snickers_chocolate_wrapper",
    "snickers_chocolate_wrapper": "snickers_chocolate_wrapper",
    "dairy_milk_wrapper": "cadbury_dairy_milk_chocolate_wrapper",
    "cadbury_dairy_milk_chocolate_wrapper": "cadbury_dairy_milk_chocolate_wrapper",

    # E-waste
    "samsung_ram_stick": "samsung_ram_stick",
    "ram_stick": "samsung_ram_stick",
    
    "cable": "usb_cable",
    "usb_cable": "usb_cable",
    "circuit_board": "circuit_board",
    "pcb": "circuit_board",
    "motherboard": "circuit_board",
}




# ---------------------------------------------------------
# Rejected result
# ---------------------------------------------------------

def _rejected_result(
    status,
    action,
    match_type="none",
    matched_profile_id=None,
    match_distance=None,
    similarity_score=0.0,
    metadata=None,
    target_weight_g=None,
    margin_g=None,
):
    return {
        "matched_profile_id": matched_profile_id,
        "match_type": match_type,
        "match_distance": match_distance,
        "similarity_score": similarity_score,
        "target_weight_g": target_weight_g,
        "margin_g": margin_g,
        "metadata": metadata or {},
        "final_decision": {
            "status": status,
            "action": action,
            "hardware_route_signal": "R",
            "reward_eligible": False,
        },
    }


# ---------------------------------------------------------
# Waste profile evaluation
# ---------------------------------------------------------

def evaluate_with_rag(label: str, real_weight_g: float):
    """
    Retrieve a known waste profile from the local JSON file
    using exact label/alias matching, then validate its weight,
    recyclability and reference rate.

    This lightweight implementation does not perform semantic
    embedding search. Unknown labels are rejected.
    """

    # Validate label
    if not label or not label.strip():
        return _rejected_result(
            status="UNRECOGNIZED",
            action="Reject item. No visual label was detected.",
        )

    # Validate weight
    try:
        real_weight_g = float(real_weight_g)
    except (TypeError, ValueError):
        real_weight_g = 0.0

    if not real_weight_g > 0:
        return _rejected_result(
            status="REJECTED",
            action="Reject item. Invalid weight reading.",
        )

    # Exact label/alias lookup
    normalized_label = _normalize_label(label)
    profile_id = LABEL_ALIASES.get(normalized_label)

    if not profile_id or profile_id not in PROFILE_BY_ID:
        return _rejected_result(
            status="UNRECOGNIZED",
            action=(
                f"Reject item. No known waste profile matches "
                f"the detected label '{label}'."
            ),
            match_type="no_exact_match",
        )

    item_info = PROFILE_BY_ID[profile_id]

        # Optional source retrieval; this does not determine reward eligibility.
    source_retrieval = fetch_reference_page(
        item_info.get("rate_source_url")
    )

    result_metadata = dict(item_info)
    result_metadata["source_retrieval"] = source_retrieval

    # Weight validation
    try:
        target_weight = float(
            item_info.get("typical_empty_weight_g", 0)
        )
        tolerance_percent = float(
            item_info.get("weight_tolerance_percent", 0)
        )
    except (TypeError, ValueError):
        return _rejected_result(
            status="RAG_ERROR",
            action="Reject item. Waste profile has invalid weight data.",
            match_type="invalid_profile",
            matched_profile_id=profile_id,
            metadata=item_info,
        )

    margin = target_weight * tolerance_percent / 100
    weight_difference_g = abs(real_weight_g - target_weight)

    weight_is_valid = (
        target_weight > 0
        and weight_difference_g <= margin
    )

    # Material routing
    category = str(item_info.get("category", "")).lower()

    if "metal" in category:
        expected_signal = "M"
    elif "plastic" in category:
        expected_signal = "P"
    elif "e-waste" in category or "ewaste" in category:
        expected_signal = "E"
    else:
        expected_signal = "R"

    # Reference rate validation
    try:
        rate = float(item_info.get("rate_inr_per_kg", 0))
    except (TypeError, ValueError):
        rate = 0.0

    rate_status = str(item_info.get("rate_status", "")).lower()

    rate_available = (
        rate > 0
        and rate_status in {
            "reference",
            "verified",
            "fallback_reference",
        "provisional_reference",
        }
    )

    recyclable = bool(item_info.get("recyclable", False))

    # Final decision
    if (
        weight_is_valid
        and expected_signal in {"P", "M", "E"}
        and rate_available
        and recyclable
    ):
        status = "VERIFIED_CLEAN"
        action = (
            f"Accept item. Route to "
            f"{item_info.get('category', 'material').upper()} bin."
        )
        hardware_signal = expected_signal
        reward_eligible = True

    else:
        status = "REJECTED"

        if not weight_is_valid:
            action = (
                "Reject item. Measured weight does not match "
                "the retrieved waste profile."
            )
        elif not rate_available:
            action = (
                "Reject item. No valid reference rate is available "
                "for this material."
            )
        elif not recyclable:
            action = (
                "Reject item. Retrieved material is not marked "
                "as recyclable."
            )
        else:
            action = (
                "Reject item. Material classification could not "
                "be safely validated."
            )

        hardware_signal = "R"
        reward_eligible = False

    return {
        "matched_profile_id": profile_id,
        "matched_item": item_info.get("item"),
        "category": item_info.get("category"),
        "material": item_info.get("material"),
        "match_type": "exact_label",
        "match_distance": None,
        "similarity_score": 1.0,
        "target_weight_g": target_weight,
        "margin_g": round(margin, 2),
        "weight_difference_g": round(weight_difference_g, 2),
        "rate_inr_per_kg": rate,
        "metadata": result_metadata,
        "final_decision": {
            "status": status,
            "action": action,
            "hardware_route_signal": hardware_signal,
            "reward_eligible": reward_eligible,
        },
    }
