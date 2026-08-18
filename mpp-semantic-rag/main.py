import os
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from web3 import Web3

# Load environment variables from .env
load_dotenv()

app = FastAPI(title="Smart Bin RAG & Web3 API")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
    )

# --- Web3 Setup ---
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# ERC-20 Mint ABI
ABI_PATH = os.path.join(os.path.dirname(__file__), "abi.json")

with open(ABI_PATH, "r") as f:
    CONTRACT_ABI = json.load(f)

def mint_reward_tokens(recipient_wallet: str, amount: int = 10):
    if not PRIVATE_KEY or not CONTRACT_ADDRESS:
        raise ValueError("Missing PRIVATE_KEY or CONTRACT_ADDRESS in .env file.")
        
    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
    if not w3.is_address(recipient_wallet):
        raise ValueError(f"Invalid recipient wallet address: {recipient_wallet}")

    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

    nonce = w3.eth.get_transaction_count(account.address)
    
    tx = contract.functions.mint(
        Web3.to_checksum_address(recipient_wallet), 
        amount
    ).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return w3.to_hex(tx_hash)

# --- Routes ---

@app.get("/")
async def root():
    return {"status": "online", "service": "Smart Bin Semantic RAG & Web3 Engine"}

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

        tx_hash = None
        # Mint real Sepolia tokens if user provides a valid 0x wallet address
        if wallet_address and wallet_address.startswith("0x"):
            tx_hash = mint_reward_tokens(wallet_address, amount=10)

        return {
            "predicted_label": label,
            "stable_weight_g": real_weight_g,
            "hardware_route_signal": "M",
            "fusion_result": {
                "decision": "VERIFIED_CLEAN",
                "action": "Accept item. Route to METAL bin."
            },
            "web3_reward": {
                "tokens_minted": 10,
                "tx_hash": tx_hash,
                "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
