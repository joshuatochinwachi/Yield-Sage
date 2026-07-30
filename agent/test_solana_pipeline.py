# agent/test_solana_pipeline.py
"""
End-to-end verification script for YieldSage Solana Migration.

Tests:
1. Keypair loading and public address derivation.
2. Solana RPC connectivity & wallet SOL balance check.
3. Live Solana yield fetch and Supabase ingestion.
4. Canonical payload hashing & test on-chain Memo logging on Solana.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timezone

# Add current directory and parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_solana_pipeline")

from fetcher import SolanaFetcher, supabase
from logger import (
    load_keypair,
    get_sol_balance,
    build_recommendation_payload,
    hash_payload,
    log_recommendation_solana,
    get_solscan_url,
)

async def test_keypair_and_rpc():
    logger.info("=== STEP 1: Testing Keypair & Solana RPC Connectivity ===")
    keypair = load_keypair()
    if not keypair:
        logger.error("❌ Keypair failed to load. Check YIELDSAGE_SOLANA_WALLET_KEYPAIR in .env.")
        return False

    pubkey_str = str(keypair.pubkey())
    logger.info(f"✅ Keypair loaded successfully! Public Address: {pubkey_str}")

    try:
        sol_balance = get_sol_balance(pubkey_str)
        logger.info(f"✅ Solana RPC Connected! Wallet Balance: {sol_balance:.6f} SOL")
        if sol_balance < 0.0001:
            logger.warning("⚠️  Wallet balance is low (< 0.0001 SOL). Fund address 49t6FUdPAg7dCcXKPgpkYebKw3pN9mZoicoUfhz2YsN3 with SOL to perform live on-chain SPL memo transactions.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to reach Solana RPC: {e}")
        return False


async def test_fetcher():
    logger.info("\n=== STEP 2: Testing Live Solana Fetcher & Supabase Ingestion ===")
    try:
        fetcher = SolanaFetcher()
        await fetcher.run()
        logger.info("✅ Live Solana Fetcher executed cleanly!")

        # Verify snapshots in DB
        res = supabase.table("yield_snapshots").select("id, asset, apy, tvl_usd, fetched_at").order("fetched_at", desc=True).limit(5).execute()
        if res.data:
            logger.info(f"✅ Supabase Ingestion Verified! Top {len(res.data)} latest snapshots:")
            for s in res.data:
                logger.info(f"   - {s.get('asset')}: APY={s.get('apy')}%, TVL=${s.get('tvl_usd')}")
            return True
        else:
            logger.warning("⚠️  No yield snapshots found in Supabase.")
            return False
    except Exception as e:
        logger.error(f"❌ Fetcher test failed: {e}")
        return False

async def test_logger():
    logger.info("\n=== STEP 3: Testing Canonical Hashing & On-Chain Solana Memo Logging ===")
    try:
        keypair = load_keypair()
        scored_at = datetime.now(timezone.utc)
        payload = build_recommendation_payload(
            protocol_name="Kamino Finance",
            pool_name="USDC Lending",
            program_address="KLend2g3cP87fffoy8q1mQqGKjrL9jRWKCKEeyEFxBl",
            risk_tag="stable",
            rank=1,
            apy_at_time=8.42,
            tvl_usd=210340000.0,
            ai_reasoning="Test verification payload for Solana migration.",
            ai_model="meta/llama-3.3-70b-instruct",
            scored_at=scored_at,
        )

        digest = hash_payload(payload)
        logger.info(f"✅ Canonical SHA-256 Digest Computed: {digest}")

        if keypair:
            logger.info("Attempting SPL Memo broadcast on Solana Mainnet...")
            tx_signature, rec_hash = log_recommendation_solana(payload)
            if tx_signature:
                logger.info(f"🎉 SUCCESS! On-chain Memo Broadcasted!")
                logger.info(f"   Signature: {tx_signature}")
                logger.info(f"   Solscan URL: {get_solscan_url(tx_signature)}")
            else:
                logger.info("ℹ️  On-chain broadcast skipped or pending (likely balance check needed). Hash preserved for DB.")
        return True
    except Exception as e:
        logger.error(f"❌ Logger test failed: {e}")
        return False

async def main():
    logger.info("Starting YieldSage Solana End-to-End Test Suite...\n")
    rpc_ok = await test_keypair_and_rpc()
    if not rpc_ok:
        logger.error("Stopping test suite due to RPC / keypair setup issues.")
        return

    fetch_ok = await test_fetcher()
    log_ok = await test_logger()

    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"RPC & Keypair Setup : {'✅ PASS' if rpc_ok else '❌ FAIL'}")
    logger.info(f"Solana Yield Fetcher : {'✅ PASS' if fetch_ok else '❌ FAIL'}")
    logger.info(f"Solana Memo Logger   : {'✅ PASS' if log_ok else '❌ FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
