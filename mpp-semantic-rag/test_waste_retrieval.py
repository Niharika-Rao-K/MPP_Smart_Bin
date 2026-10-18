from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


BASE_DIR = Path(__file__).resolve().parent


# Connect to existing ChromaDB
chroma_client = chromadb.PersistentClient(
    path=str(BASE_DIR / "chroma_db")
)

embedding_function = embedding_functions.DefaultEmbeddingFunction()

collection = chroma_client.get_collection(
    name="waste_knowledge",
    embedding_function=embedding_function,
)


# Test query
query = "Coca-Cola aluminum beverage can metal"


results = collection.query(
    query_texts=[query],
    n_results=2,
)


print("\nQUERY:")
print(query)

print("\nRETRIEVED DOCUMENTS:")

for document in results["documents"][0]:
    print("--------------------------------")
    print(document)

print("\nMETADATA:")

for metadata in results["metadatas"][0]:
    print("--------------------------------")
    print(metadata)
