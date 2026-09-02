import os
import chromadb

# Initialize local ChromaDB client
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = chroma_client.get_or_create_collection(name="recycling_standards")

# Baseline reference database (Material mappings, target weight, error margin, bin category)
REFERENCE_METADATA = {
    "coca_cola_can": {
        "target_weight_g": 13.5,
        "margin_g": 3.0,
        "category": "metal",
        "signal": "M",
        "resale_rate_per_kg": 28.0,
        "quality_factor": 1.0
    },
    "pepsi_can": {
        "target_weight_g": 14.0,
        "margin_g": 3.0,
        "category": "metal",
        "signal": "M",
        "resale_rate_per_kg": 28.0,
        "quality_factor": 1.0
    },
    "water_bottle": {
        "target_weight_g": 18.0,
        "margin_g": 4.0,
        "category": "plastic",
        "signal": "P",
        "resale_rate_per_kg": 20.0,
        "quality_factor": 0.9
    },
    "snack_wrapper": {
        "target_weight_g": 5.0,
        "margin_g": 2.0,
        "category": "plastic",
        "signal": "P",
        "resale_rate_per_kg": 14.0,
        "quality_factor": 0.7
    },
    "circuit_board": {
        "target_weight_g": 45.0,
        "margin_g": 10.0,
        "category": "ewaste",
        "signal": "E",
        "resale_rate_per_kg": 180.0,
        "quality_factor": 1.2
    }
}
LABEL_ALIASES = {
    "bottle": "water_bottle",
    "plastic_bottle": "water_bottle",
    "water_bottle": "water_bottle",

    "can": "coca_cola_can",
    "tin_can": "coca_cola_can",
    "soda_can": "coca_cola_can",
    "coca_cola_can": "coca_cola_can",
    "pepsi_can": "pepsi_can",

    "wrapper": "snack_wrapper",
    "snack_wrapper": "snack_wrapper",
    "chocolate_wrapper": "snack_wrapper",

    "circuit_board": "circuit_board",
    "pcb": "circuit_board",
    "motherboard": "circuit_board"
}

def evaluate_with_rag(label: str, real_weight_g: float):
    """
    Returns one safe material decision:
    P = Plastic, M = Metal, E = E-Waste, R = Reject.
    """

    normalized_label = label.lower().strip().replace(" ", "_")
    profile_label = LABEL_ALIASES.get(normalized_label, normalized_label)

    matched_profile_id = None
    match_type = "none"
    match_distance = None
    item_info = None

    # Exact known-profile match.
    if profile_label in REFERENCE_METADATA:
        matched_profile_id = profile_label
        item_info = REFERENCE_METADATA[profile_label]
        match_type = "exact"

    # Semantic ChromaDB fallback for an unknown YOLO label.
    else:
        try:
            results = collection.query(
                query_texts=[label],
                n_results=1,
                include=["metadatas", "distances"]
            )

            metadatas = results.get("metadatas", [[]])
            distances = results.get("distances", [[]])
            ids = results.get("ids", [[]])

            if metadatas and metadatas[0]:
                item_info = metadatas[0][0]
                matched_profile_id = ids[0][0] if ids and ids[0] else None
                match_distance = distances[0][0] if distances and distances[0] else None
                match_type = "semantic"

        except Exception:
            item_info = None

    # Unknown items are safely rejected.
    if not item_info:
        return {
            "matched_profile_id": None,
            "match_type": "none",
            "match_distance": None,
            "similarity_score": 0.0,
            "target_weight_g": None,
            "margin_g": None,
            "metadata": {},
            "final_decision": {
                "status": "UNRECOGNIZED",
                "action": "Reject item. No reliable material profile was found.",
                "hardware_route_signal": "R",
                "reward_eligible": False
            }
        }

    target_weight = float(item_info.get("target_weight_g", 0))
    margin = float(item_info.get("margin_g", 0))
    expected_signal = item_info.get("signal", "R")

    # Approximate normalized similarity for dashboard display.
    similarity_score = (
        1.0 if match_type == "exact"
        else round(1 / (1 + float(match_distance or 999)), 3)
    )

    # Semantic matches that are too weak are not accepted.
    semantic_match_is_safe = (
        match_type == "exact"
        or similarity_score >= 0.85
    )

    weight_difference_g = abs(real_weight_g - target_weight)
    weight_is_valid = weight_difference_g <= margin
    valid_signal = expected_signal in {"P", "M", "E"}

    if semantic_match_is_safe and weight_is_valid and valid_signal:
        status = "VERIFIED_CLEAN"
        action = f"Accept item. Route to {item_info.get('category', 'material').upper()} bin."
        hardware_signal = expected_signal
        reward_eligible = True
    else:
        status = "REJECTED"
        action = "Reject item. Classification confidence or weight validation failed."
        hardware_signal = "R"
        reward_eligible = False

    return {
        "matched_profile_id": matched_profile_id,
        "match_type": match_type,
        "match_distance": match_distance,
        "similarity_score": similarity_score,
        "target_weight_g": target_weight,
        "margin_g": margin,
        "weight_difference_g": weight_difference_g,
        "metadata": item_info,
        "final_decision": {
            "status": status,
            "action": action,
            "hardware_route_signal": hardware_signal,
            "reward_eligible": reward_eligible
        }
    }
