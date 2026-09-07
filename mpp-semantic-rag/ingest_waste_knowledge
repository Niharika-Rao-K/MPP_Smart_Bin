import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


# --------------------------------------------------
# 1. Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "waste_knowledge.json"


# --------------------------------------------------
# 2. Load waste knowledge
# --------------------------------------------------

with open(DATA_FILE, "r", encoding="utf-8") as f:
    waste_items = json.load(f)


# --------------------------------------------------
# 3. Initialize ChromaDB
# --------------------------------------------------

chroma_client = chromadb.PersistentClient(
    path=str(BASE_DIR / "chroma_db")
)

embedding_function = embedding_functions.DefaultEmbeddingFunction()

collection = chroma_client.get_or_create_collection(
    name="waste_knowledge",
    embedding_function=embedding_function,
)


# --------------------------------------------------
# 4. Convert knowledge records into documents
# --------------------------------------------------

documents = []
metadatas = []
ids = []


for index, item in enumerate(waste_items):

    document = (
        f"Item: {item['item']}. "
        f"Brand: {item['brand']}. "
        f"Category: {item['category']}. "
        f"Material: {item['material']}. "
        f"Container type: {item['container_type']}. "
        f"Volume: {item['volume_ml']} ml. "
        f"Typical empty weight: "
        f"{item['typical_empty_weight_g']} grams. "
        f"Weight tolerance: "
        f"{item['weight_tolerance_percent']} percent. "
        f"Recyclable: {item['recyclable']}."
    )

    documents.append(document)

    metadatas.append({
        "item": item["item"],
        "brand": item["brand"],
        "category": item["category"],
        "material": item["material"],
        "container_type": item["container_type"],
        "volume_ml": (
            item["volume_ml"]
            if item["volume_ml"] is not None
            else 0
        ),
        "typical_empty_weight_g": item["typical_empty_weight_g"],
        "weight_tolerance_percent": item["weight_tolerance_percent"],
        "recyclable": item["recyclable"],
    })

    ids.append(f"waste_{index + 1}")


# --------------------------------------------------
# 5. Store in ChromaDB
# --------------------------------------------------

collection.upsert(
    ids=ids,
    documents=documents,
    metadatas=metadatas,
)


# --------------------------------------------------
# 6. Confirmation
# --------------------------------------------------

print("Waste knowledge successfully added to ChromaDB.")
print(f"Total records: {collection.count()}")
