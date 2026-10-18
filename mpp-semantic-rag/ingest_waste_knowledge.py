import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "waste_knowledge.json"
CHROMA_DIR = BASE_DIR / "chroma_db"


# ---------------------------------------------------------
# Load waste knowledge
# ---------------------------------------------------------

with open(DATA_FILE, "r", encoding="utf-8") as f:
    waste_items = json.load(f)


# ---------------------------------------------------------
# Connect to ChromaDB
# ---------------------------------------------------------

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

embedding_function = embedding_functions.DefaultEmbeddingFunction()

collection = chroma_client.get_or_create_collection(
    name="waste_knowledge",
    embedding_function=embedding_function,
)


# ---------------------------------------------------------
# Prepare documents
# ---------------------------------------------------------

documents = []
metadatas = []
ids = []


for index, item in enumerate(waste_items):

    document = (
        f"Item: {item['item']}. "
        f"Brand: {item['brand']}. "
        f"Product: {item['product']}. "
        f"Object: {item['object']}. "
        f"Category: {item['category']}. "
        f"Material: {item['material']}. "
        f"Material category: {item['material_category']}. "
        f"Packaging type: {item['packaging_type']}. "
        f"Container type: {item['container_type']}. "
        f"Volume: {item['volume_ml']} ml. "
        f"Typical empty weight: "
        f"{item['typical_empty_weight_g']} grams. "
        f"Weight tolerance: "
        f"{item['weight_tolerance_percent']} percent. "
        f"Recyclable: {item['recyclable']}. "
        f"Reference rate: "
        f"{item['rate_inr_per_kg']} INR per kg. "
        f"Region: {item['region']}. "
        f"Rate status: {item['rate_status']}."
    )

    documents.append(document)

    # Chroma metadata values must be primitive types.
    metadatas.append({
        "item": item["item"],
        "brand": item["brand"],
        "product": item["product"],
        "object": item["object"],
        "category": item["category"],
        "material": item["material"],
        "material_category": item["material_category"],
        "packaging_type": item["packaging_type"],
        "container_type": item["container_type"],
        "volume_ml": (
            item["volume_ml"]
            if item["volume_ml"] is not None
            else 0
        ),
        "typical_empty_weight_g": item["typical_empty_weight_g"],
        "weight_tolerance_percent": item["weight_tolerance_percent"],
        "recyclable": item["recyclable"],
        "rate_inr_per_kg": (
            item["rate_inr_per_kg"]
            if item["rate_inr_per_kg"] is not None
            else 0.0
        ),
        "rate_source": item["rate_source"] or "",
        "rate_source_url": item["rate_source_url"] or "",
        "rate_effective_date": item["rate_effective_date"] or "",
        "region": item["region"],
        "rate_status": item["rate_status"],
    })

    ids.append(f"waste_{index + 1}")


# ---------------------------------------------------------
# Update ChromaDB
# ---------------------------------------------------------

collection.upsert(
    ids=ids,
    documents=documents,
    metadatas=metadatas,
)


# ---------------------------------------------------------
# Result
# ---------------------------------------------------------

print("Waste knowledge successfully added to ChromaDB.")
print(f"Collection: {collection.name}")
print(f"Total records: {collection.count()}")