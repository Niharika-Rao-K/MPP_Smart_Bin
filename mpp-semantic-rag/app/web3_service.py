import os
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0xb2dd28b8f372a8ff49EeC1ffe43d40D69fDA0B00")
PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load ABI
abi_path = os.path.join(os.path.dirname(__file__), "abi", "RecycleToken.json")
with open(abi_path, "r") as f:
    CONTRACT_ABI = json.load(f)

def mint_recycle_tokens(recipient_address: str, amount: int = 10):
    if not PRIVATE_KEY:
        return {"status": "SKIPPED", "reason": "ADMIN_PRIVATE_KEY missing in .env environment."}
    
    if not w3.is_connected():
        return {"status": "FAILED", "reason": "Failed to connect to Sepolia RPC provider."}

    try:
        account = w3.eth.account.from_key(PRIVATE_KEY)
        contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

        nonce = w3.eth.get_transaction_count(account.address)
        
        tx = contract.functions.mintReward(
            Web3.to_checksum_address(recipient_address), 
            amount
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': w3.eth.gas_price
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return {
            "status": "CONFIRMED",
            "tx_hash": w3.to_hex(tx_hash)
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
