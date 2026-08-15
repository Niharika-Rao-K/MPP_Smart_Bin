import os
import chromadb

# Connect to local ChromaDB instance
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# Get or create collection
collection = chroma_client.get_or_create_collection(name="recycling_standards")

# Define baseline training documents & reference metadata
documents = [
    "Aluminum beverage can standard thin metal beverage container 13.5g",
    "PET clear plastic water bottle standard screw cap 18g",
    "Multilayer plastic snack food wrapper aluminum foil lining 5g",
    "Printed circuit board electronic waste motherboards scrap 45g"
]

metadatas = [
    {"target_weight_g": 13.5, "margin_g": 3.0, "category": "metal", "signal": "M"},
    {"target_weight_g": 18.0, "margin_g": 4.0, "category": "plastic", "signal": "W"},
    {"target_weight_g": 5.0, "margin_g": 2.0, "category": "wrapper", "signal": "W"},
    {"target_weight_g": 45.0, "margin_g": 10.0, "category": "ewaste", "signal": "E"}
]

ids = ["doc_metal", "doc_plastic", "doc_wrapper", "doc_ewaste"]

collection.add(documents=documents, metadatas=metadatas, ids=ids)

print(f"Successfully seeded {collection.count()} items into ChromaDB!")
