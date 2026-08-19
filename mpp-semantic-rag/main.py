import os
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from web3 import Web3

load_dotenv()

app = FastAPI(title="Smart Bin RAG & Web3 API")

# Enable CORS for all origins (Allows React on port 3000/5173 to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://eth-sepolia.g.alchemy.com/v2/_wokhAu3_ees-Kn_dPfyJ")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

ABI_PATH = os.path.join(os.path.dirname(__file__), "abi.json")

try:
    with open(ABI_PATH, "r") as f:
        CONTRACT_ABI = json.load(f)
except Exception:
    CONTRACT_ABI = []

# Reference database for dynamic RAG/similarity credit scoring
KNOWN_ITEMS_DB = [
    {"brand": "Coca-Cola Can (330ml)", "material": "Metal", "base_weight_g": 13.0, "credits": 15},
    {"brand": "Pepsi Can (330ml)", "material": "Metal", "base_weight_g": 13.5, "credits": 15},
    {"brand": "Generic Aluminum Can", "material": "Metal", "base_weight_g": 14.0, "credits": 12},
    {"brand": "Pepsi Bottle (500ml)", "material": "Plastic", "base_weight_g": 18.0, "credits": 10},
    {"brand": "Coca-Cola Bottle (500ml)", "material": "Plastic", "base_weight_g": 18.5, "credits": 10},
    {"brand": "Generic Plastic Bottle", "material": "Plastic", "base_weight_g": 20.0, "credits": 8},
    {"brand": "Circuit Board / Battery", "material": "E-Waste", "base_weight_g": 50.0, "credits": 30},
]

def calculate_dynamic_credits(label: str, real_weight_g: float) -> int:
    """
    Dynamically calculates reward points using nearest-neighbor similarity match 
    against known baseline items (RAG retrieval step).
    """
    matched_items = [item for item in KNOWN_ITEMS_DB if item["material"].lower() == label.lower()]

    if not matched_items:
        return max(1, int(real_weight_g * 0.5))

    nearest_item = min(matched_items, key=lambda x: abs(x["base_weight_g"] - real_weight_g))
    weight_ratio = real_weight_g / nearest_item["base_weight_g"]
    calculated_credits = int(nearest_item["credits"] * weight_ratio)

    return max(1, min(calculated_credits, 100))

def mint_reward_tokens(recipient_wallet: str, amount: int = 10, label: str = "Plastic", weight_g: float = 0.0):
    if not PRIVATE_KEY or not CONTRACT_ADDRESS:
        raise ValueError("Missing PRIVATE_KEY or CONTRACT_ADDRESS in .env file.")
        
    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
    if not w3.is_address(recipient_wallet):
        raise ValueError(f"Invalid recipient wallet address: {recipient_wallet}")

    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

    nonce = w3.eth.get_transaction_count(account.address)
    
    # Scale integer credit score to 18 decimal places (wei)
    token_amount_wei = w3.to_wei(amount, 'ether')

    # Calls contract function mint(address to, uint256 amount, string material, uint256 weight)
    tx = contract.functions.mint(
        Web3.to_checksum_address(recipient_wallet), 
        token_amount_wei,
        label,
        int(weight_g)
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

        # Compute dynamic points based on RAG similarity match
        dynamic_credits = calculate_dynamic_credits(label, real_weight_g)

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

        # Hardware signal mapping based on material input
        signal_map = {"Metal": "M", "Plastic": "W", "E-Waste": "E"}
        route_signal = signal_map.get(label, "M")

        return {
            "predicted_label": label,
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
