import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "waste_knowledge.json"
CHROMA_DATA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "waste_knowledge"


def profile_id(profile):
    """Stable ID derived from the canonical profile item name."""
    import re

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(profile["item"]).lower()
    ).strip("_")


def build_document(profile):
    """Build descriptive text for semantic retrieval."""
    fields = [
        ("Item", "item"),
        ("Brand", "brand"),
        ("Product", "product"),
        ("Object", "object"),
        ("Category", "category"),
        ("Material", "material"),
        ("Material category", "material_category"),
        ("Packaging type", "packaging_type"),
        ("Container type", "container_type"),
        ("Volume in ml", "volume_ml"),
        ("Typical empty weight in grams", "typical_empty_weight_g"),
        ("Weight tolerance percent", "weight_tolerance_percent"),
        ("Recyclable flag", "recyclable"),
        ("Rate in INR per kg", "rate_inr_per_kg"),
        ("Rate status", "rate_status"),
        ("Rate source", "rate_source"),
        ("Rate effective date", "rate_effective_date"),
        ("Region", "region"),
    ]

    parts = [
        f"{label}: {profile[key]}"
        for label, key in fields
        if profile.get(key) is not None
    ]

    # Include the labels currently produced by the vision classifier.
    item = str(profile.get("item", "")).lower()

    if item == "coca-cola 330ml aluminum can":
        parts.append(
            "Related classifier label: diet_coke. "
            "This is a label alias, not independent brand verification."
        )

    if item == "snack wrapper":
        parts.append(
            "Related classifier label: snickers_wrapper. "
            "This is a generic wrapper candidate, not brand verification."
        )

    return ". ".join(parts)


def build_metadata(profile):
    """Chroma metadata must contain supported scalar values."""
    metadata = {
        "profile_id": profile_id(profile),
        "item": str(profile["item"]),
    }

    for key in (
        "brand",
        "product",
        "object",
        "category",
        "material",
        "material_category",
        "packaging_type",
        "container_type",
        "rate_source",
        "rate_source_url",
        "rate_effective_date",
        "rate_status",
        "region",
    ):
        value = profile.get(key)
        if value is not None:
            metadata[key] = str(value)

    for key in (
        "volume_ml",
        "typical_empty_weight_g",
        "weight_tolerance_percent",
        "rate_inr_per_kg",
    ):
        value = profile.get(key)
        if value is not None:
            metadata[key] = float(value)

    metadata["recyclable"] = bool(profile.get("recyclable", False))
    return metadata


def main():
    if not KNOWLEDGE_PATH.exists():
        raise FileNotFoundError(
            f"Knowledge file not found: {KNOWLEDGE_PATH}"
        )

    profiles = json.loads(
        KNOWLEDGE_PATH.read_text(encoding="utf-8")
    )

    if not isinstance(profiles, list) or not profiles:
        raise ValueError(
            "Waste knowledge JSON must be a non-empty list."
        )

    required_fields = {
        "item",
        "category",
        "material",
        "material_category",
        "typical_empty_weight_g",
        "weight_tolerance_percent",
        "rate_status",
    }

    for profile in profiles:
        missing = required_fields - profile.keys()
        if missing:
            raise ValueError(
                f"Profile {profile.get('item')!r} is missing: "
                f"{sorted(missing)}"
            )

    ids = [profile_id(p) for p in profiles]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate profile IDs found in waste_knowledge.json."
        )

    client = chromadb.PersistentClient(
        path=str(CHROMA_DATA_PATH)
    )

    embedding_function = (
        embedding_functions.DefaultEmbeddingFunction()
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"description": "Indexed from data/waste_knowledge.json"},
    )

    documents = [build_document(p) for p in profiles]
    metadatas = [build_metadata(p) for p in profiles]

    # Remove obsolete records from this collection only.
    existing = collection.get()
    existing_ids = set(existing.get("ids") or [])
    current_ids = set(ids)
    obsolete_ids = sorted(existing_ids - current_ids)

    if obsolete_ids:
        collection.delete(ids=obsolete_ids)

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"Knowledge file: {KNOWLEDGE_PATH}")
    print(f"ChromaDB path: {CHROMA_DATA_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Canonical profiles: {len(profiles)}")
    print(f"Obsolete records removed: {len(obsolete_ids)}")
    print(f"Indexed profile count: {collection.count()}")


if __name__ == "__main__":
    main()
