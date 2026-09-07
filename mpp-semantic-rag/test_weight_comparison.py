from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


BASE_DIR = Path(__file__).resolve().parent


# --------------------------------------------------
# 1. Connect to ChromaDB
# --------------------------------------------------

chroma_client = chromadb.PersistentClient(
    path=str(BASE_DIR / "chroma_db")
)

embedding_function = embedding_functions.DefaultEmbeddingFunction()

collection = chroma_client.get_collection(
    name="waste_knowledge",
    embedding_function=embedding_function,
)


# --------------------------------------------------
# 2. Simulate YOLO output
# --------------------------------------------------

predicted_item = "Coca-Cola aluminum beverage can"
actual_weight_g = 15.0


# --------------------------------------------------
# 3. Retrieve matching waste knowledge
# --------------------------------------------------

results = collection.query(
    query_texts=[predicted_item],
    n_results=1,
)

metadata = results["metadatas"][0][0]


print("\nYOLO PREDICTION:")
print(predicted_item)

print("\nACTUAL WEIGHT:")
print(f"{actual_weight_g} g")

print("\nRETRIEVED KNOWLEDGE:")
print(metadata)


# --------------------------------------------------
# 4. Extract expected weight information
# --------------------------------------------------

expected_weight = metadata["typical_empty_weight_g"]
tolerance_percent = metadata["weight_tolerance_percent"]


# --------------------------------------------------
# 5. Calculate acceptable weight range
# --------------------------------------------------

minimum_weight = expected_weight * (
    1 - tolerance_percent / 100
)

maximum_weight = expected_weight * (
    1 + tolerance_percent / 100
)


# --------------------------------------------------
# 6. Compare actual weight with expected range
# --------------------------------------------------

is_within_range = (
    minimum_weight
    <= actual_weight_g
    <= maximum_weight
)


print("\nEXPECTED WEIGHT:")
print(f"{expected_weight} g")

print("\nACCEPTABLE RANGE:")
print(
    f"{minimum_weight:.2f} g - "
    f"{maximum_weight:.2f} g"
)


# --------------------------------------------------
# 7. Final decision
# --------------------------------------------------

if is_within_range:
    decision = "PURE"
else:
    decision = "IMPURE"


print("\nFINAL DECISION:")
print(decision)
