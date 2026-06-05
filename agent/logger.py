# agent/logger.py
# On-Chain Verifiability Layer for YieldSage
# Logs SHA-256 recommendation hashes as 0-MNT memo transactions on Mantle Network

import hashlib
import json
import os
import time
import logging
from datetime import datetime, timezone
from web3 import Web3

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
MANTLE_RPC_URL = os.environ.get("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
PRIVATE_KEY = os.environ.get("YIELDSAGE_WALLET_PRIVATE_KEY")
MANTLE_CHAIN_ID = 5000          # Mantle mainnet
MANTLESCAN_BASE = "https://mantlescan.xyz/tx/"

# ── Web3 Setup ────────────────────────────────────────────────────────────────
def get_web3() -> Web3:
    """Returns a connected Web3 instance. Raises if RPC is unreachable."""
    w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"[logger] Cannot connect to Mantle RPC: {MANTLE_RPC_URL}")
    return w3

# ── Core Functions ────────────────────────────────────────────────────────────
def build_recommendation_payload(
    protocol_name: str,
    pool_name: str,
    pool_address: str,
    risk_tag: str,
    rank: int,
    apy_at_time: float,
    tvl_usd: float,
    ai_reasoning: str,
    ai_model: str,
    scored_at: datetime,
    dune_query_id: str = "7595582",
) -> dict:
    """
    Builds the canonical payload dict that will be hashed and logged on-chain.
    All numeric fields are stored as strings to ensure hash determinism.
    scored_at must be a UTC datetime set BEFORE the LLM call.
    """
    return {
        "version": "1.0",
        "source": f"dune_query_{dune_query_id}",
        "scored_at": scored_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risk_tag": risk_tag,
        "rank": rank,
        "protocol_name": protocol_name,
        "pool_name": pool_name,
        "pool_address": pool_address.lower(),   # Normalise address casing
        "apy_at_time": f"{float(apy_at_time):.4f}",
        "tvl_usd": f"{float(tvl_usd):.2f}",
        "ai_reasoning": ai_reasoning.strip(),
        "ai_model": ai_model,
        "chain": "mantle",
        "chain_id": MANTLE_CHAIN_ID,
    }

def hash_payload(payload: dict) -> str:
    """
    Produces a deterministic SHA-256 hex digest of the recommendation payload.
    sort_keys=True and no extra whitespace ensure identical output regardless
    of Python dict insertion order.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def log_recommendation_onchain(
    payload: dict,
    max_retries: int = 3,
    retry_delay_seconds: float = 15.0,
) -> tuple[str | None, str | None]:
    """
    Sends a 0-value self-transaction on Mantle with the recommendation hash
    embedded in the data field as UTF-8 bytes: b"yieldsage:<sha256_hex>"
    Returns:
        (tx_hash_hex, rec_hash_hex) on success
        (None, rec_hash_hex) on failure — rec_hash is always returned for DB storage
    """
    if not PRIVATE_KEY:
        logger.warning("[logger] YIELDSAGE_WALLET_PRIVATE_KEY not set. Skipping on-chain log.")
        rec_hash = hash_payload(payload)
        return None, rec_hash

    rec_hash = hash_payload(payload)
    memo = f"yieldsage:{rec_hash}".encode("utf-8")

    for attempt in range(1, max_retries + 1):
        try:
            w3 = get_web3()
            account = w3.eth.account.from_key(PRIVATE_KEY)
            nonce = w3.eth.get_transaction_count(account.address, "pending")
            gas_price = w3.eth.gas_price
            tx = {
                "from":     account.address,
                "to":       account.address,    # Self-transfer — no funds move
                "value":    0,
                "gas":      50000,
                "gasPrice": gas_price,
                "nonce":    nonce,
                "data":     memo,
                "chainId":  MANTLE_CHAIN_ID,
            }
            signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash_bytes = w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = tx_hash_bytes.hex()
            logger.info(f"[logger] ✅ On-chain log success (attempt {attempt}): {tx_hash_hex}")
            logger.info(f"[logger]    View: {MANTLESCAN_BASE}{tx_hash_hex}")
            return tx_hash_hex, rec_hash
        except Exception as e:
            logger.error(f"[logger] ❌ Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay_seconds * attempt)   # Exponential backoff: 15s, 30s
            else:
                logger.critical(
                    f"[logger] All {max_retries} retries exhausted for hash {rec_hash}. "
                    f"Storing hash without tx_hash."
                )
                return None, rec_hash

def get_mantlescan_url(tx_hash: str) -> str:
    """Returns the public Mantlescan explorer URL for a given transaction hash."""
    return f"{MANTLESCAN_BASE}{tx_hash}"
