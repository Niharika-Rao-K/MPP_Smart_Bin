from pathlib import Path

import chromadb

CHROMA_DATA_PATH = Path(__file__).resolve().parents[2] / "chroma_db"

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DATA_PATH)
)

collection = chroma_client.get_or_create_collection(
    name="recycling_standards"
)

documents = [
    (
        "Coca Cola can, Pepsi can, aluminum beverage can, soft drink can, "
        "thin metal beverage container, aluminium tin, 13.5 grams."
    ),
    (
        "PET water bottle, clear plastic water bottle, mineral water bottle, "
        "plastic drink bottle, screw-cap bottle, 18 grams."
    ),
    (
        "Snack wrapper, chocolate wrapper, chips packet, food wrapper, "
        "multilayer plastic wrapper, foil-lined plastic wrapper, 5 grams."
    ),
    (
        "Printed circuit board, PCB, motherboard, electronic circuit board, "
        "electronic waste, e-waste scrap, 45 grams."
    )
]

metadatas = [
    {
        "target_weight_g": 13.5,
        "margin_g": 3.0,
        "category": "metal",
        "signal": "M",
        "resale_rate_per_kg": 28.0,
        "quality_factor": 1.0
    },
    {
        "target_weight_g": 18.0,
        "margin_g": 4.0,
        "category": "plastic",
        "signal": "P",
        "resale_rate_per_kg": 20.0,
        "quality_factor": 0.9
    },
    {
        "target_weight_g": 5.0,
        "margin_g": 2.0,
        "category": "plastic",
        "signal": "P",
        "resale_rate_per_kg": 14.0,
        "quality_factor": 0.7
    },
    {
        "target_weight_g": 45.0,
        "margin_g": 10.0,
        "category": "ewaste",
        "signal": "E",
        "resale_rate_per_kg": 180.0,
        "quality_factor": 1.2
    }
]

ids = [
    "coca_cola_can",
    "water_bottle",
    "snack_wrapper",
    "circuit_board"
]

collection.upsert(
    documents=documents,
    metadatas=metadatas,
    ids=ids
)

print(f"Successfully seeded {collection.count()} material profiles into ChromaDB.")
