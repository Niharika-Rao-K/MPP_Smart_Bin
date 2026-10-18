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


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# GLOBAL EXCEPTION HANDLER
# ---------------------------------------------------------

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
# CHROMADB / RAG
# ---------------------------------------------------------

CHROMA_PATH = os.path.join(
    os.path.dirname(__file__),
    "mpp-semantic-rag",
    "chroma_db"
)

try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    embedding_model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    collections = chroma_client.list_collections()

    collection_name = (
        collections[0].name
        if collections
        else "brand_rewards"
    )

    chroma_collection = chroma_client.get_or_create_collection(
        name=collection_name
    )

    print(
        f"--- ChromaDB successfully loaded from "
        f"'{CHROMA_PATH}' "
        f"(Collection: {collection_name}) ---"
    )

except Exception as e:

    print(
        f"--- ChromaDB Load Warning: {e}. "
        f"Falling back to default scoring. ---"
    )

    chroma_collection = None
    embedding_model = None


# ---------------------------------------------------------
# WEB3 CONFIGURATION
# ---------------------------------------------------------

# IMPORTANT:
# Keep the RPC URL in .env.
# Do NOT put a real Alchemy API key directly in source code.

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")


ABI_PATH = os.path.join(
    os.path.dirname(__file__),
    "abi.json"
)

try:
    with open(ABI_PATH, "r") as f:
        CONTRACT_ABI = json.load(f)

except Exception:
    CONTRACT_ABI = []


# ---------------------------------------------------------
# RAG REWARD CALCULATION
# ---------------------------------------------------------

def calculate_dynamic_credits_rag(
    label: str,
    real_weight_g: float
) -> tuple[int, str]:

    """
    real_weight_g is ALWAYS grams.

    Example:
        18 -> 18 grams
        25.5 -> 25.5 grams
        100 -> 100 grams

    No automatic kg/gram conversion happens here.
    """

    if real_weight_g <= 0:
        raise ValueError("Weight must be greater than zero.")

    matched_brand = "Generic Item Match"

    weight_in_grams = float(real_weight_g)

    if chroma_collection and embedding_model:

        try:

            query_embedding = embedding_model.encode(
                label
            ).tolist()

            results = chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=1
            )

            if (
                results
                and results.get("metadatas")
                and len(results["metadatas"][0]) > 0
            ):

                metadata = results["metadatas"][0][0]

                matched_brand = metadata.get(
                    "brand",
                    metadata.get(
                        "name",
                        "Matched Brand"
                    )
                )

                base_credits = float(
                    metadata.get(
                        "credits",
                        metadata.get(
                            "base_credits",
                            10
                        )
                    )
                )

                base_weight_g = float(
                    metadata.get(
                        "base_weight_g",
                        15.0
                    )
                )

                weight_ratio = (
                    weight_in_grams / base_weight_g
                    if base_weight_g > 0
                    else 1.0
                )

                calculated_credits = int(
                    base_credits * weight_ratio
                )

                return (
                    max(
                        1,
                        min(
                            calculated_credits,
                            200
                        )
                    ),
                    matched_brand
                )

        except Exception as err:

            print(
                f"RAG Query Error: {err}"
            )

    # Fallback reward
    fallback_credits = max(
        1,
        int(weight_in_grams * 0.05)
    )

    return (
        min(fallback_credits, 200),
        matched_brand
    )


# ---------------------------------------------------------
# BLOCKCHAIN MINT
# ---------------------------------------------------------

def mint_reward_tokens(
    recipient_wallet: str,
    amount: int = 10,
    label: str = "Plastic",
    weight_g: float = 0.0
):

    if not PRIVATE_KEY:
        raise ValueError(
            "PRIVATE_KEY is missing from .env"
        )

    if not CONTRACT_ADDRESS:
        raise ValueError(
            "CONTRACT_ADDRESS is missing from .env"
        )

    if not SEPOLIA_RPC_URL:
        raise ValueError(
            "SEPOLIA_RPC_URL is missing from .env"
        )

    w3 = Web3(
        Web3.HTTPProvider(
            SEPOLIA_RPC_URL
        )
    )

    if not w3.is_connected():
        raise ConnectionError(
            "Could not connect to Sepolia RPC."
        )

    checksum_wallet = Web3.to_checksum_address(
        recipient_wallet
    )

    account = w3.eth.account.from_key(
        PRIVATE_KEY
    )

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(
            CONTRACT_ADDRESS
        ),
        abi=CONTRACT_ABI
    )

    nonce = w3.eth.get_transaction_count(
        account.address
    )

    # $RECYCLE token amount
    token_amount_wei = w3.to_wei(
        amount,
        "ether"
    )

    # Weight is already in grams.
    weight_in_grams = int(
        round(weight_g)
    )

    tx = contract.functions.mint(
        checksum_wallet,
        token_amount_wei,
        label,
        weight_in_grams
    ).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed_tx = w3.eth.account.sign_transaction(
        tx,
        private_key=PRIVATE_KEY
    )

    raw_tx = getattr(
        signed_tx,
        "raw_transaction",
        getattr(
            signed_tx,
            "rawTransaction",
            None
        )
    )

    tx_hash = w3.eth.send_raw_transaction(
        raw_tx
    )

    return w3.to_hex(tx_hash)


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get("/")
async def root():

    return {
        "message": "Smart Bin RAG & Web3 API is running"
    }


# ---------------------------------------------------------
# RAG / WEB3 EVALUATION
# ---------------------------------------------------------

@app.post("/api/rag/evaluate")
async def evaluate_sensor_fusion(
    label: str = Form(...),
    real_weight_g: float = Form(...),
    wallet_address: str = Form(""),
    bin_id: str = Form("UNKNOWN"),
    image: Optional[UploadFile] = File(None)
):

    try:

        # -------------------------------------------------
        # VALIDATE WEIGHT
        # -------------------------------------------------

        if real_weight_g <= 0:
            raise HTTPException(
                status_code=400,
                detail="Weight must be greater than zero grams."
            )

        # -------------------------------------------------
        # IMAGE
        # -------------------------------------------------

        image_filename = None

        if image:

            image_filename = image.filename

            # At this stage we only receive the image.
            # Actual image classification will be integrated
            # once the classifier/model is connected.
            await image.read()

        # -------------------------------------------------
        # VALIDATE CATEGORY
        # -------------------------------------------------

        allowed_labels = {
            "Plastic",
            "Metal",
            "E-Waste"
        }

        if label not in allowed_labels:

            return {
                "status": "REJECTED",
                "predicted_label": label,
                "stable_weight_g": real_weight_g,
                "hardware_route_signal": "R",
                "calculated_credits": 0,

                "fusion_result": {
                    "decision": "REJECTED",
                    "action": (
                        "Waste category could not be "
                        "verified."
                    )
                },

                "web3_reward": {
                    "tokens_minted": 0,
                    "tx_hash": None,
                    "explorer_url": None
                }
            }

        # -------------------------------------------------
        # RAG REWARD CALCULATION
        # -------------------------------------------------

        dynamic_credits, matched_brand = (
            calculate_dynamic_credits_rag(
                label,
                real_weight_g
            )
        )

        # -------------------------------------------------
        # ROUTING
        # -------------------------------------------------

        signal_map = {
            "Plastic": "P",
            "Metal": "M",
            "E-Waste": "E"
        }

        route_signal = signal_map[label]

        # -------------------------------------------------
        # ACCEPT ITEM
        # -------------------------------------------------

        tx_hash = None

        if wallet_address and wallet_address.strip():

            try:

                tx_hash = mint_reward_tokens(
                    recipient_wallet=wallet_address.strip(),
                    amount=dynamic_credits,
                    label=label,
                    weight_g=real_weight_g
                )

            except Exception as web3_err:

                print(
                    "--- WEB3 TRANSACTION ERROR TRACE ---"
                )

                print(web3_err)

                print(
                    "------------------------------------"
                )

                # IMPORTANT:
                # If blockchain minting fails, do NOT
                # report tokens as successfully minted.
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Waste was verified, but the "
                        "blockchain reward transaction failed."
                    )
                )

        # -------------------------------------------------
        # SUCCESS RESPONSE
        # -------------------------------------------------

        return {

            "status": "SUCCESS",

            "predicted_label": label,

            "matched_brand_reference": matched_brand,

            "stable_weight_g": real_weight_g,

            "hardware_route_signal": route_signal,

            "calculated_credits": dynamic_credits,

            "bin_id": bin_id,

            "image_filename": image_filename,

            "fusion_result": {

                "decision": "VERIFIED_CLEAN",

                "action": (
                    f"Accept item. Route to "
                    f"{label.upper()} bin."
                )
            },

            "web3_reward": {

                "tokens_minted": (
                    dynamic_credits
                    if tx_hash
                    else 0
                ),

                "tx_hash": tx_hash,

                "explorer_url": (
                    f"https://sepolia.etherscan.io/tx/{tx_hash}"
                    if tx_hash
                    else None
                )
            }
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
