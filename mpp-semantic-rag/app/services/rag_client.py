import os

import chromadb
from chromadb.utils import embedding_functions


# ---------------------------------------------------------
# ChromaDB configuration
# ---------------------------------------------------------

CHROMA_DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "chroma_db"
)

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DATA_PATH
)

embedding_function = embedding_functions.DefaultEmbeddingFunction()

collection = chroma_client.get_collection(
    name="waste_knowledge",
    embedding_function=embedding_function
)


# ---------------------------------------------------------
# RAG confidence threshold
# ---------------------------------------------------------

# Lower ChromaDB distance means a closer semantic match.
#
# This threshold was selected from the current six-record
# waste knowledge base:
#
# Known examples:
#   Pepsi can        ~0.541
#   Snack wrapper    ~0.673
#   PET bottle       ~0.702
#   Coca-Cola can    ~0.794
#   USB cable        ~1.044
#
# Unknown examples:
#   Glass bottle     ~1.102
#   Wooden object    ~1.404
#   Paper cup        ~1.460
#
# This is a prototype threshold and should be re-evaluated
# when the knowledge base grows.

RAG_DISTANCE_THRESHOLD = 1.08


# ---------------------------------------------------------
# Label normalization
# ---------------------------------------------------------

LABEL_ALIASES = {
    "bottle": "water bottle",
    "plastic_bottle": "PET water bottle",
    "water_bottle": "PET water bottle",

    "can": "aluminum beverage can",
    "tin_can": "aluminum beverage can",
    "soda_can": "aluminum beverage can",
    "coca_cola_can": "Coca-Cola aluminum can",
    "pepsi_can": "Pepsi aluminum can",

    "wrapper": "snack wrapper",
    "snack_wrapper": "snack wrapper",
    "chocolate_wrapper": "chocolate wrapper",

    "usb_cable": "USB cable",
    "cable": "USB cable",

    "circuit_board": "circuit board",
    "pcb": "circuit board",
    "motherboard": "circuit board"
}


# ---------------------------------------------------------
# Helper: rejected RAG result
# ---------------------------------------------------------

def _rejected_result(
    status: str,
    action: str,
    match_type: str = "none",
    matched_profile_id=None,
    match_distance=None,
    similarity_score=0.0,
    metadata=None,
    target_weight_g=None,
    margin_g=None
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
            "reward_eligible": False
        }
    }


# ---------------------------------------------------------
# RAG evaluation
# ---------------------------------------------------------

def evaluate_with_rag(
    label: str,
    real_weight_g: float
):
    """
    Retrieve the most relevant waste profile from ChromaDB
    and validate it against the measured weight.

    Returns:
        - retrieved material information
        - semantic match distance
        - similarity score
        - applicable reference rate
        - weight validation
        - final acceptance/rejection decision
    """

    # -----------------------------------------------------
    # Validate visual label
    # -----------------------------------------------------

    if not label or not label.strip():
        return _rejected_result(
            status="UNRECOGNIZED",
            action="Reject item. No visual label was detected."
        )

    # -----------------------------------------------------
    # Validate measured weight
    # -----------------------------------------------------

    if real_weight_g <= 0:
        return _rejected_result(
            status="REJECTED",
            action="Reject item. Invalid weight reading."
        )

    # -----------------------------------------------------
    # Normalize label
    # -----------------------------------------------------

    normalized_label = (
        label.lower()
        .strip()
        .replace(" ", "_")
    )

    query_label = LABEL_ALIASES.get(
        normalized_label,
        label
    )

    # -----------------------------------------------------
    # Retrieve from ChromaDB
    # -----------------------------------------------------

    try:
        results = collection.query(
            query_texts=[query_label],
            n_results=1,
            include=[
                "metadatas",
                "documents",
                "distances"
            ]
        )

    except Exception as exc:
        return _rejected_result(
            status="RAG_ERROR",
            action=(
                "Reject item. RAG retrieval failed: "
                f"{str(exc)}"
            ),
            match_type="error"
        )

    # -----------------------------------------------------
    # Extract retrieval result
    # -----------------------------------------------------

    metadatas = results.get(
        "metadatas",
        [[]]
    )

    distances = results.get(
        "distances",
        [[]]
    )

    ids = results.get(
        "ids",
        [[]]
    )

    if not metadatas or not metadatas[0]:
        return _rejected_result(
            status="UNRECOGNIZED",
            action=(
                "Reject item. No reliable waste profile "
                "was found."
            )
        )

    item_info = metadatas[0][0]

    matched_profile_id = (
        ids[0][0]
        if ids and ids[0]
        else None
    )

    match_distance = (
        distances[0][0]
        if distances and distances[0]
        else None
    )

    # -----------------------------------------------------
    # Calculate similarity score
    # -----------------------------------------------------

    if match_distance is None:
        similarity_score = 0.0
    else:
        similarity_score = round(
            1 / (1 + float(match_distance)),
            3
        )

    # -----------------------------------------------------
    # Semantic confidence check
    # -----------------------------------------------------

    if (
        match_distance is None
        or float(match_distance) > RAG_DISTANCE_THRESHOLD
    ):
        return _rejected_result(
            status="UNRECOGNIZED",
            action=(
                "Reject item. The detected item does not "
                "match a known waste profile with "
                "sufficient semantic confidence."
            ),
            match_type="low_confidence",
            matched_profile_id=matched_profile_id,
            match_distance=match_distance,
            similarity_score=similarity_score,
            metadata=item_info
        )

    # -----------------------------------------------------
    # Retrieve expected weight
    # -----------------------------------------------------

    target_weight = float(
        item_info.get(
            "typical_empty_weight_g",
            0
        )
    )

    # -----------------------------------------------------
    # Calculate allowed weight margin
    # -----------------------------------------------------

    tolerance_percent = float(
        item_info.get(
            "weight_tolerance_percent",
            0
        )
    )

    margin = (
        target_weight
        * tolerance_percent
        / 100
    )

    # -----------------------------------------------------
    # Compare actual and expected weight
    # -----------------------------------------------------

    weight_difference_g = abs(
        real_weight_g - target_weight
    )

    weight_is_valid = (
        target_weight > 0
        and weight_difference_g <= margin
    )

    # -----------------------------------------------------
    # Determine material routing
    # -----------------------------------------------------

    category = str(
        item_info.get(
            "category",
            ""
        )
    ).lower()

    if "metal" in category:
        expected_signal = "M"

    elif "plastic" in category:
        expected_signal = "P"

    elif (
        "e-waste" in category
        or "ewaste" in category
    ):
        expected_signal = "E"

    else:
        expected_signal = "R"

    # -----------------------------------------------------
    # Validate reference rate
    # -----------------------------------------------------

    rate = item_info.get(
        "rate_inr_per_kg",
        0
    )

    try:
        rate = float(rate)
    except (TypeError, ValueError):
        rate = 0.0

    rate_status = str(
        item_info.get(
            "rate_status",
            ""
        )
    ).lower()

    rate_available = (
        rate > 0
        and rate_status in {
            "reference",
            "verified",
            "fallback_reference"
        }
    )

    # -----------------------------------------------------
    # Final decision
    # -----------------------------------------------------

    if (
        weight_is_valid
        and expected_signal in {
            "P",
            "M",
            "E"
        }
        and rate_available
        and bool(
            item_info.get(
                "recyclable",
                False
            )
        )
    ):
        status = "VERIFIED_CLEAN"

        action = (
            f"Accept item. Route to "
            f"{item_info.get('category', 'material').upper()} "
            f"bin."
        )

        hardware_signal = expected_signal
        reward_eligible = True

    else:
        status = "REJECTED"

        if not weight_is_valid:
            action = (
                "Reject item. Measured weight does not "
                "match the retrieved waste profile."
            )

        elif not rate_available:
            action = (
                "Reject item. No valid reference rate "
                "is available for this material."
            )

        elif not item_info.get(
            "recyclable",
            False
        ):
            action = (
                "Reject item. Retrieved material is "
                "not marked as recyclable."
            )

        else:
            action = (
                "Reject item. Material classification "
                "could not be safely validated."
            )

        hardware_signal = "R"
        reward_eligible = False

    # -----------------------------------------------------
    # Return result
    # -----------------------------------------------------

    return {
        "matched_profile_id": matched_profile_id,
        "match_type": "semantic",
        "match_distance": match_distance,
        "similarity_score": similarity_score,

        "target_weight_g": target_weight,
        "margin_g": round(
            margin,
            2
        ),
        "weight_difference_g": round(
            weight_difference_g,
            2
        ),

        "rate_inr_per_kg": rate,

        "metadata": item_info,

        "final_decision": {
            "status": status,
            "action": action,
            "hardware_route_signal": hardware_signal,
            "reward_eligible": reward_eligible
        }
    }
