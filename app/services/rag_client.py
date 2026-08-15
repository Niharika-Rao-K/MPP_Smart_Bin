import os
import chromadb

# Initialize local ChromaDB client
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = chroma_client.get_or_create_collection(name="recycling_standards")

# Baseline reference database (Material mappings, target weight, error margin, bin category)
REFERENCE_METADATA = {
    "coca_cola_can": {"target_weight_g": 13.5, "margin_g": 3.0, "category": "metal", "signal": "M"},
    "pepsi_can": {"target_weight_g": 14.0, "margin_g": 3.0, "category": "metal", "signal": "M"},
    "water_bottle": {"target_weight_g": 18.0, "margin_g": 4.0, "category": "plastic", "signal": "W"},
    "snack_wrapper": {"target_weight_g": 5.0, "margin_g": 2.0, "category": "wrapper", "signal": "W"},
    "circuit_board": {"target_weight_g": 45.0, "margin_g": 10.0, "category": "ewaste", "signal": "E"}
}

def evaluate_with_rag(label: str, real_weight_g: float):
    """
    Evaluates visual label against ChromaDB metadata and verifies weight bounds.
    Returns routing signals: 'W' (Wrapper/Plastic), 'M' (Metal), 'E' (E-Waste), 'R' (Reject).
    """
    normalized_label = label.lower().replace(" ", "_")
    
    # 1. Check direct baseline match
    if normalized_label in REFERENCE_METADATA:
        item_info = REFERENCE_METADATA[normalized_label]
    else:
        # 2. Semantic fallback via ChromaDB vector lookup for unknown brands
        try:
            results = collection.query(query_texts=[label], n_results=1)
            if results and results['metadatas'][0]:
                item_info = results['metadatas'][0][0]
            else:
                # Default safety fallback if completely unrecognized
                item_info = {"target_weight_g": 15.0, "margin_g": 5.0, "category": "unknown", "signal": "R"}
        except Exception:
            item_info = {"target_weight_g": 15.0, "margin_g": 5.0, "category": "unknown", "signal": "R"}

    target_weight = item_info.get("target_weight_g", 15.0)
    margin = item_info.get("margin_g", 5.0)
    expected_signal = item_info.get("signal", "R")

    # 3. Sensor Fusion Weight Verification (Liquid/Contamination Detection)
    weight_diff = abs(real_weight_g - target_weight)
    
    if weight_diff <= margin:
        status = "VERIFIED_CLEAN"
        action = f"Accept item. Route to {item_info.get('category', 'bin').upper()} bin."
        hardware_signal = expected_signal
    else:
        status = "CONTAMINATION_DETECTED"
        action = "Reject item. Anomaly or liquid remaining inside."
        hardware_signal = "R"  # Triggers rapid shaking reject loop on pan-tilt servo

    return {
        "matched_label": normalized_label,
        "target_weight_g": target_weight,
        "margin_g": margin,
        "final_decision": {
            "status": status,
            "action": action,
            "hardware_route_signal": hardware_signal
        }
    }
