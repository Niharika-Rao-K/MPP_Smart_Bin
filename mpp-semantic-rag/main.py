import os
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from web3 import Web3

import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()

app = FastAPI(title="Smart Bin RAG & Web3 API")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://solid-succotash-97w5vgqj54vr277wv-3000.app.github.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
    return JSONResponse(
        status_code=getattr(exc, "status_code", 500),
        content={"detail": detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
    )

# ---------------------------------------------------------
# CHROMADB & SEMANTIC RAG INITIALIZATION
# ---------------------------------------------------------
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "mpp-semantic-rag", "chroma_db")

try:
    # Initialize Persistent ChromaDB client targeting the vector DB folder
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Initialize sentence transformer model for query embeddings
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Get existing collection or create default
    collections = chroma_client.list_collections()
    collection_name = collections[0].name if collections else "brand_rewards"
    chroma_collection = chroma_client.get_or_create_collection(name=collection_name)
    print(f"--- ChromaDB successfully loaded from '{CHROMA_PATH}' (Collection: {collection_name}) ---")
except Exception as e:
    print(f"--- ChromaDB Load Warning: {e}. Falling back to default scoring. ---")
    chroma_collection = None
    embedding_model = None

# Web3 Configuration
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://eth-sepolia.g.alchemy.com/v2/_wokhAu3_ees-Kn_dPfyJ")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

ABI_PATH = os.path.join(os.path.dirname(__file__), "abi.json")

try:
    with open(ABI_PATH, "r") as f:
        CONTRACT_ABI = json.load(f)
except Exception:
    CONTRACT_ABI = []


def calculate_dynamic_credits_rag(label: str, real_weight_g: float) -> tuple[int, str]:
    """
    Performs semantic vector search against ChromaDB vector store.
    Matches unknown inputs to nearest known brands and calculates proportional rewards.
    """
    matched_brand = "Generic Item Match"
    
    # Normalize weight: Ensure real_weight_g is in grams (e.g., if sent as 1.85 kg -> 1850 g)
    weight_in_grams = real_weight_g * 1000.0 if real_weight_g < 100.0 else real_weight_g
    
    if chroma_collection and embedding_model:
        try:
            # Generate vector embedding for the input label/description
            query_embedding = embedding_model.encode(label).tolist()
            
            # Retrieve top 1 semantic match from ChromaDB
            results = chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=1
            )

            if results and results.get("metadatas") and len(results["metadatas"][0]) > 0:
                metadata = results["metadatas"][0][0]
                matched_brand = metadata.get("brand", metadata.get("name", "Matched Brand"))
                
                # Retrieve reference credits and base weight (in grams) from DB
                base_credits = float(metadata.get("credits", metadata.get("base_credits", 10)))
                base_weight_g = float(metadata.get("base_weight_g", 15.0))

                # Proportional scaling based on actual weight vs reference weight
                weight_ratio = weight_in_grams / base_weight_g if base_weight_g > 0 else 1.0
                
                # Calculate reward points with a reasonable ceiling
                calculated_credits = int(base_credits * weight_ratio)
                return max(1, min(calculated_credits, 200)), matched_brand
        except Exception as err:
            print(f"RAG Query Error: {err}")

    # Fallback calculation if ChromaDB search fails
    fallback_credits = max(1, int(weight_in_grams * 0.05))
    return min(fallback_credits, 200), matched_brand


def mint_reward_tokens(recipient_wallet: str, amount: int = 10, label: str = "Plastic", weight_g: float = 0.0):
    if not PRIVATE_KEY or not CONTRACT_ADDRESS:
        raise ValueError("Missing PRIVATE_KEY or CONTRACT_ADDRESS in .env file.")
        
    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
    checksum_wallet = Web3.to_checksum_address(recipient_wallet)

    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

    nonce = w3.eth.get_transaction_count(account.address)
    
    # Scale integer credit score to 18 decimal places (wei) for standard ERC-20 contract
    token_amount_wei = w3.to_wei(amount, 'ether')

    # Ensure weight passed to contract is an integer in grams
    weight_in_grams = int(weight_g * 1000) if weight_g < 100 else int(weight_g)

    tx = contract.functions.mint(
        checksum_wallet, 
        token_amount_wei,
        label,
        weight_in_grams
    ).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    
    raw_tx = getattr(signed_tx, "raw_transaction", getattr(signed_tx, "rawTransaction", None))
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    return w3.to_hex(tx_hash)


@app.get("/")
async def root():
    return {"message": "Smart Bin RAG & Web3 API is running"}


@app.post("/api/rag/evaluate")
async def evaluate_sensor_fusion(
    label: str = Form(...),
    real_weight_g: float = Form(...),
    wallet_address: str = Form(""),
    image: Optional[UploadFile] = File(None)
):
    try:
        if image:
            await image.read()

        # Execute true vector RAG similarity match with standardized weight calculation
        dynamic_credits, matched_brand = calculate_dynamic_credits_rag(label, real_weight_g)

        tx_hash = None
        if wallet_address and wallet_address.strip().startswith("0x"):
            try:
                tx_hash = mint_reward_tokens(
                    recipient_wallet=wallet_address.strip(),
                    amount=dynamic_credits,
                    label=label,
                    weight_g=real_weight_g
                )
            except Exception as web3_err:
                print(f"--- WEB3 TRANSACTION ERROR TRACE ---")
                print(web3_err)
                print(f"------------------------------------")
                tx_hash = None

        signal_map = {"Metal": "M", "Plastic": "W", "E-Waste": "E"}
        route_signal = signal_map.get(label, "M")

        return {
            "predicted_label": label,
            "matched_brand_reference": matched_brand,
            "stable_weight_g": real_weight_g,
            "hardware_route_signal": route_signal,
            "calculated_credits": dynamic_credits,
            "fusion_result": {
                "decision": "VERIFIED_CLEAN",
                "action": f"Accept item. Route to {label.upper()} bin."
            },
            "web3_reward": {
                "tokens_minted": dynamic_credits if tx_hash else 0,
                "tx_hash": tx_hash,
                "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
