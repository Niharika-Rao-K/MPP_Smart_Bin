import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
BLOCKCHAIN_PRIVATE_KEY = os.getenv("BLOCKCHAIN_PRIVATE_KEY")


# ---------------------------------------------------------
# Validate configuration
# ---------------------------------------------------------

if not SEPOLIA_RPC_URL:
    raise RuntimeError("SEPOLIA_RPC_URL is missing from .env")

if not CONTRACT_ADDRESS:
    raise RuntimeError("CONTRACT_ADDRESS is missing from .env")

if not BLOCKCHAIN_PRIVATE_KEY:
    raise RuntimeError("BLOCKCHAIN_PRIVATE_KEY is missing from .env")


# ---------------------------------------------------------
# Web3 connection
# ---------------------------------------------------------

w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))

if not w3.is_connected():
    raise RuntimeError("Could not connect to Sepolia RPC")


# Normalize contract address
CONTRACT_ADDRESS = Web3.to_checksum_address(CONTRACT_ADDRESS)


# ---------------------------------------------------------
# Load ABI
# ---------------------------------------------------------

ABI_PATH = BASE_DIR / "app" / "abi" / "RecycleToken.json"

if not ABI_PATH.exists():
    raise RuntimeError(
        f"RecycleToken ABI not found at: {ABI_PATH}"
    )

import json

with ABI_PATH.open("r", encoding="utf-8") as abi_file:
    CONTRACT_ABI = json.load(abi_file)


# ---------------------------------------------------------
# Contract
# ---------------------------------------------------------

contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=CONTRACT_ABI
)


# ---------------------------------------------------------
# Backend signer
# ---------------------------------------------------------

ACCOUNT = w3.eth.account.from_key(BLOCKCHAIN_PRIVATE_KEY)

BACKEND_ADDRESS = ACCOUNT.address


# ---------------------------------------------------------
# Verify contract ownership
# ---------------------------------------------------------

CONTRACT_OWNER = contract.functions.owner().call()

if BACKEND_ADDRESS.lower() != CONTRACT_OWNER.lower():
    raise RuntimeError(
        "Backend signer is NOT the owner of the RecycleToken contract.\n"
        f"Backend signer: {BACKEND_ADDRESS}\n"
        f"Contract owner: {CONTRACT_OWNER}"
    )


# ---------------------------------------------------------
# Mint recycling reward
# ---------------------------------------------------------

def mint_recycling_reward(
    user_wallet_address: str,
    amount_tokens: float,
    material: str,
    weight_grams: float
):
    """
    Mint RECYCLE tokens to a user's wallet.

    The backend signer must be the owner of the RecycleToken
    contract because mint() is protected by onlyOwner.
    """

    # -----------------------------------------------------
    # Validate user wallet
    # -----------------------------------------------------

    try:
        user_wallet_address = Web3.to_checksum_address(
            user_wallet_address
        )
    except ValueError:
        return {
            "status": "FAILED",
            "reason": "Invalid recipient wallet address"
        }

    # -----------------------------------------------------
    # Validate reward
    # -----------------------------------------------------

    if amount_tokens <= 0:
        return {
            "status": "FAILED",
            "reason": "Reward amount must be greater than zero"
        }

    # -----------------------------------------------------
    # Validate weight
    # -----------------------------------------------------

    if weight_grams <= 0:
        return {
            "status": "FAILED",
            "reason": "Weight must be greater than zero"
        }

    # -----------------------------------------------------
    # Convert values
    # -----------------------------------------------------

    # RecycleToken inherits OpenZeppelin ERC20, which uses
    # 18 decimals by default.
    token_decimals = contract.functions.decimals().call()

    token_amount = int(
        round(amount_tokens * (10 ** token_decimals))
    )

    # Solidity expects uint256 for weightGrams.
    weight_grams_uint = int(round(weight_grams))

    # -----------------------------------------------------
    # Get current blockchain state
    # -----------------------------------------------------

    try:
        nonce = w3.eth.get_transaction_count(
            BACKEND_ADDRESS,
            "pending"
        )

        chain_id = w3.eth.chain_id

        gas_price = w3.eth.gas_price

    except Exception as exc:
        return {
            "status": "FAILED",
            "reason": f"Failed to read blockchain state: {str(exc)}"
        }

    # -----------------------------------------------------
    # Build mint transaction
    # -----------------------------------------------------

    try:
        transaction = contract.functions.mint(
            user_wallet_address,
            token_amount,
            material,
            weight_grams_uint
        ).build_transaction(
            {
                "from": BACKEND_ADDRESS,
                "nonce": nonce,
                "chainId": chain_id,
                "gas": 300000,
                "gasPrice": gas_price,
            }
        )

    except ContractLogicError as exc:
        return {
            "status": "FAILED",
            "reason": f"Smart contract rejected mint: {str(exc)}"
        }

    except Exception as exc:
        return {
            "status": "FAILED",
            "reason": f"Failed to build mint transaction: {str(exc)}"
        }

    # -----------------------------------------------------
    # Sign transaction
    # -----------------------------------------------------

    try:
        signed_transaction = w3.eth.account.sign_transaction(
            transaction,
            BLOCKCHAIN_PRIVATE_KEY
        )

    except Exception as exc:
        return {
            "status": "FAILED",
            "reason": f"Transaction signing failed: {str(exc)}"
        }

    # -----------------------------------------------------
    # Send transaction
    # -----------------------------------------------------

    try:
        tx_hash = w3.eth.send_raw_transaction(
            signed_transaction.raw_transaction
        )

    except Exception as exc:
        return {
            "status": "FAILED",
            "reason": f"Failed to send transaction: {str(exc)}"
        }

    # -----------------------------------------------------
    # Wait for confirmation
    # -----------------------------------------------------

    try:
        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=120
        )

    except Exception as exc:
        return {
            "status": "PENDING",
            "reason": f"Transaction sent but confirmation timed out: {str(exc)}",
            "tx_hash": tx_hash.hex(),
            "explorer_url": (
                f"https://sepolia.etherscan.io/tx/{tx_hash.hex()}"
            ),
        }

    # -----------------------------------------------------
    # Check transaction status
    # -----------------------------------------------------

    if receipt["status"] != 1:
        return {
            "status": "FAILED",
            "reason": "Blockchain transaction reverted",
            "tx_hash": tx_hash.hex(),
            "explorer_url": (
                f"https://sepolia.etherscan.io/tx/{tx_hash.hex()}"
            ),
        }

    # -----------------------------------------------------
    # Success
    # -----------------------------------------------------

    return {
        "status": "SUCCESS",
        "tx_hash": tx_hash.hex(),
        "explorer_url": (
            f"https://sepolia.etherscan.io/tx/{tx_hash.hex()}"
        ),
        "tokens_minted": amount_tokens,
        "recipient": user_wallet_address,
        "material": material,
        "weight_grams": weight_grams_uint,
        "token_decimals": token_decimals,
        "raw_token_amount": token_amount,
        "block_number": receipt["blockNumber"],
        "gas_used": receipt["gasUsed"],
    }
