from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import chromadb
import random

app = FastAPI(title="Smart Recycling Bin RAG & Fusion Backend")

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChromaDB Client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
try:
    collection = chroma_client.get_collection("recycling_standards")
except Exception:
    collection = None

@app.get("/")
def read_root():
    return {"status": "online", "system": "Smart Recycling Bin Sensor Fusion API"}

@app.post("/deposit")
async def process_deposit(
    image: UploadFile = File(...),
    weight: float = Form(...),
    wallet_address: str = Form("0x0000000000000000000000000000000000000000")
):
    """
    Simulates ESP32-CAM + Load Cell Sensor Fusion Pipeline
    """
    # 1. Simulated YOLOv8 Detection (Mocked for testing without GPU/Hardware)
    mock_labels = ["coca_cola_can", "snack_wrapper", "water_bottle", "unknown_object"]
    predicted_label = random.choice(["coca_cola_can", "snack_wrapper", "water_bottle"])
    confidence = round(random.uniform(0.85, 0.98), 2)

    # 2. ChromaDB RAG Lookup
    rag_metadata = {}
    target_signal = "R" # Default Reject
    
    if collection:
        results = collection.query(query_texts=[predicted_label], n_results=1)
        if results and results["metadatas"] and len(results["metadatas"][0]) > 0:
            rag_metadata = results["metadatas"][0][0]
            target_signal = rag_metadata.get("signal", "R")

    # 3. Anomaly & Sensor Fusion Validation Logic
    # Example rule: Reject if actual weight exceeds target weight + margin
    target_weight = rag_metadata.get("target_weight_g", 15.0)
    margin = rag_metadata.get("margin_g", 5.0)
    
    is_anomaly = abs(weight - target_weight) > (margin + 150.0) # Reject heavy liquid contamination
    
    if is_anomaly:
        route_signal = "R"
        action = "REJECT: Anomaly or liquid contamination detected."
        tokens_earned = 0
    else:
        route_signal = target_signal
        action = f"ACCEPT: Item classified as {predicted_label}. Routing to bin {route_signal}."
        tokens_earned = 10

    # 4. Return Sensor Fusion & Web3 Response Payload
    return {
        "status": "SUCCESS" if route_signal != "R" else "REJECTED",
        "predicted_label": predicted_label,
        "confidence": confidence,
        "stable_weight_g": weight,
        "hardware_route_signal": route_signal,
        "fusion_result": {
            "decision": "VERIFIED_CLEAN" if route_signal != "R" else "CONTAMINATION_DETECTED",
            "action": action,
            "rag_result": {
                "matched_label": predicted_label,
                "metadata": rag_metadata
            }
        },
        "web3_reward": {
            "recipient_wallet": wallet_address,
            "tokens_minted": tokens_earned,
            "status": "SIMULATED_MINT"
        }
    }
