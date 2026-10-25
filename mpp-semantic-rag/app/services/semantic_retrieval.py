from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DATA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "waste_knowledge"


def retrieve_semantic_profiles(
    query: str,
    n_results: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve candidate material profiles from the local ChromaDB index.

    Distances rank candidates; they are not probabilities or proof of
    material purity, brand identity, or reward eligibility.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    if not isinstance(n_results, int) or n_results < 1:
        raise ValueError("n_results must be a positive integer")

    client = chromadb.PersistentClient(
        path=str(CHROMA_DATA_PATH)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=(
            embedding_functions.DefaultEmbeddingFunction()
        ),
    )

    total = collection.count()
    if total == 0:
        return []

    result = collection.query(
        query_texts=[query.strip()],
        n_results=min(n_results, total),
        include=["documents", "metadatas", "distances"],
    )

    documents = result["documents"][0] or []
    metadatas = result["metadatas"][0] or []
    distances = result["distances"][0] or []

    candidates = []

    for document, metadata, distance in zip(
        documents, metadatas, distances
    ):
        candidates.append({
            "profile_id": metadata.get("profile_id"),
            "item": metadata.get("item"),
            "category": metadata.get("category"),
            "material": metadata.get("material"),
            "material_category": metadata.get("material_category"),
            "typical_empty_weight_g": metadata.get(
                "typical_empty_weight_g"
            ),
            "weight_tolerance_percent": metadata.get(
                "weight_tolerance_percent"
            ),
            "rate_inr_per_kg": metadata.get("rate_inr_per_kg"),
            "rate_status": metadata.get("rate_status"),
            "rate_source": metadata.get("rate_source"),
            "rate_source_url": metadata.get("rate_source_url"),
            "distance": float(distance),
            "document": document,
        })

    return candidates
