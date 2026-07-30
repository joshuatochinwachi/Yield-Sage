# agent/logger.py
# On-Chain Verifiability Layer for YieldSage — Solana Mainnet
# Logs SHA-256 recommendation hashes as SPL Memo transactions on Solana
# SPL Memo Program: MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr

import hashlib
import json
import os
import time
import base58
import logging
from datetime import datetime, timezone

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction
from solders.message import Message

try:
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
except ImportError:
    try:
        from solana.rpc.providers.http import HTTPProvider
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts
    except ImportError:
        Client = None
        TxOpts = None

import httpx

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────────────
SOLANA_RPC_URL          = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
SOLANA_RPC_URL_FALLBACK = os.environ.get("SOLANA_RPC_URL_FALLBACK", "https://api.mainnet-beta.solana.com")
KEYPAIR_ENV             = os.environ.get("YIELDSAGE_SOLANA_WALLET_KEYPAIR") or os.environ.get("YIELDSAGE_WALLET_PRIVATE_KEY")
MEMO_PROGRAM_ID         = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
SOLSCAN_BASE            = "https://solscan.io/tx/"

# ── Keypair Loading ───────────────────────────────────────────────────────────
def load_keypair() -> Keypair | None:
    """
    Loads the agent keypair from the YIELDSAGE_SOLANA_WALLET_KEYPAIR env var.
    Supports two formats:
      - Base58 string (64-byte private key)
      - JSON array of 64 integers (Phantom/Solana-CLI export format)
    """
    if not KEYPAIR_ENV:
        logger.warning("[logger] YIELDSAGE_SOLANA_WALLET_KEYPAIR not set. Skipping on-chain Solana log.")
        return None
    try:
        # Try JSON array format first (e.g. [1,2,3,...])
        if KEYPAIR_ENV.strip().startswith("["):
            secret_bytes = bytes(json.loads(KEYPAIR_ENV))
        else:
            secret_bytes = base58.b58decode(KEYPAIR_ENV.strip())
        return Keypair.from_bytes(secret_bytes)
    except Exception as e:
        logger.error(f"[logger] Failed to load keypair from env: {e}")
        return None

def get_client(use_fallback: bool = False):
    url = SOLANA_RPC_URL_FALLBACK if use_fallback else SOLANA_RPC_URL
    if Client is not None:
        try:
            return Client(url)
        except Exception:
            pass
    return None

def get_sol_balance(pubkey_str: str, use_fallback: bool = False) -> float:
    """Queries SOL balance in lamports and converts to SOL float via RPC."""
    url = SOLANA_RPC_URL_FALLBACK if use_fallback else SOLANA_RPC_URL
    resp = httpx.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [pubkey_str]},
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    lamports = data.get("result", {}).get("value", 0)
    return lamports / 1e9


# ── Core Functions ────────────────────────────────────────────────────────────
def build_recommendation_payload(
    protocol_name: str,
    pool_name: str,
    program_address: str = None,
    pool_address: str = None,
    risk_tag: str = "moderate",
    rank: int = 1,
    apy_at_time: float = 0.0,
    tvl_usd: float = 0.0,
    ai_reasoning: str = "",
    ai_model: str = "meta/llama-3.3-70b-instruct",
    scored_at: datetime = None,
    data_source_id: str = "solana_live_pipeline",
) -> dict:
    """
    Builds the canonical payload dict for Solana recommendations.
    All numeric fields are stored as strings for hash determinism.
    scored_at MUST be set before calling the LLM.
    """
    if scored_at is None:
        scored_at = datetime.now(timezone.utc)

    target_address = program_address or pool_address or ""

    return {
        "version": "2.0",
        "source": data_source_id,
        "scored_at": scored_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risk_tag": risk_tag,
        "rank": rank,
        "protocol_name": protocol_name,
        "pool_name": pool_name,
        "program_address": target_address,
        "apy_at_time": f"{float(apy_at_time):.4f}",
        "tvl_usd": f"{float(tvl_usd):.2f}",
        "ai_reasoning": ai_reasoning.strip(),
        "ai_model": ai_model,
        "chain": "solana",
        "chain_id": 101,
    }

def hash_payload(payload: dict) -> str:
    """
    Produces a deterministic SHA-256 hex digest of the recommendation payload.
    sort_keys=True and no extra whitespace ensure identical output regardless
    of Python dict insertion order.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def get_latest_blockhash_rpc(rpc_url: str) -> str:
    """Fetches recent blockhash directly via JSON-RPC endpoint."""
    resp = httpx.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "confirmed"}]},
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    blockhash_str = data["result"]["value"]["blockhash"]
    from solders.hash import Hash
    return Hash.from_string(blockhash_str)

def send_transaction_rpc(rpc_url: str, tx_bytes: bytes) -> str:
    """Sends raw signed transaction directly via JSON-RPC endpoint."""
    b64_tx = base58.b58encode(tx_bytes).decode("utf-8")
    # Base64 is standard for sendTransaction in Solana JSON-RPC
    import base64
    b64_str = base64.b64encode(tx_bytes).decode("utf-8")
    resp = httpx.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [b64_str, {"encoding": "base64", "preflightCommitment": "confirmed"}]
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    res_data = resp.json()
    if "error" in res_data:
        raise RuntimeError(f"Solana RPC Error: {res_data['error']}")
    return res_data["result"]

def log_recommendation_solana(
    payload: dict,
    max_retries: int = 3,
    retry_delay_seconds: float = 5.0,
) -> tuple[str | None, str | None]:
    """
    Sends a Solana transaction with an SPL Memo instruction containing:
      "yieldsage:<sha256_hex>"

    Returns:
        (tx_signature, rec_hash) on success
        (None, rec_hash) on failure — rec_hash is always returned for DB storage
    """
    keypair = load_keypair()
    if not keypair:
        rec_hash = hash_payload(payload)
        return None, rec_hash

    rec_hash = hash_payload(payload)
    memo_bytes = f"yieldsage:{rec_hash}".encode("utf-8")

    for attempt in range(1, max_retries + 1):
        rpc_url = SOLANA_RPC_URL_FALLBACK if attempt > 1 else SOLANA_RPC_URL
        try:
            # 1. Fetch recent blockhash
            recent_blockhash = None
            if Client is not None:
                try:
                    client = Client(rpc_url)
                    blockhash_resp = client.get_latest_blockhash()
                    if blockhash_resp and hasattr(blockhash_resp, "value") and blockhash_resp.value:
                        recent_blockhash = blockhash_resp.value.blockhash
                except Exception as ex:
                    logger.warning(f"[logger] Client.get_latest_blockhash failed, falling back to direct JSON-RPC: {ex}")

            if recent_blockhash is None:
                recent_blockhash = get_latest_blockhash_rpc(rpc_url)

            # 2. Build SPL Memo instruction
            memo_instruction = Instruction(
                program_id=MEMO_PROGRAM_ID,
                accounts=[AccountMeta(
                    pubkey=keypair.pubkey(),
                    is_signer=True,
                    is_writable=False,
                )],
                data=memo_bytes,
            )

            # 3. Build & Sign Transaction using solders
            message = Message.new_with_blockhash(
                instructions=[memo_instruction],
                payer=keypair.pubkey(),
                blockhash=recent_blockhash,
            )
            tx = Transaction([keypair], message, recent_blockhash)

            # 4. Broadcast transaction
            tx_signature = None
            if Client is not None and TxOpts is not None:
                try:
                    client = Client(rpc_url)
                    response = client.send_transaction(
                        tx,
                        opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"),
                    )
                    if response and hasattr(response, "value") and response.value:
                        tx_signature = str(response.value)
                except Exception as ex:
                    logger.warning(f"[logger] Client.send_transaction failed, attempting direct JSON-RPC: {ex}")

            if not tx_signature:
                tx_bytes = bytes(tx)
                tx_signature = send_transaction_rpc(rpc_url, tx_bytes)

            logger.info(f"[logger] ✅ On-chain log success (attempt {attempt}): {tx_signature}")
            logger.info(f"[logger]    View: {SOLSCAN_BASE}{tx_signature}")
            return tx_signature, rec_hash

        except Exception as e:
            logger.error(f"[logger] ❌ Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay_seconds * attempt)
            else:
                logger.critical(
                    f"[logger] All {max_retries} retries exhausted for hash {rec_hash[:12]}. "
                    f"Storing hash without tx_signature."
                )
                return None, rec_hash


def get_solscan_url(tx_signature: str) -> str:
    """Returns the public Solscan explorer URL for a given transaction signature."""
    return f"{SOLSCAN_BASE}{tx_signature}"

# Backwards compatibility alias
log_recommendation_onchain = log_recommendation_solana
get_solscan_explorer_url = get_solscan_url

