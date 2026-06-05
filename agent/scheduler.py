import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fetcher import DuneFetcher, supabase
from scorer import HourlyScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize persistent singletons
fetcher = DuneFetcher()
scorer = HourlyScorer()

async def run_pipeline():
    logger.info("Starting scheduled Yield-Sage pipeline...")
    
    # 1. Fetch Dune yields with retries for transient errors
    max_retries = 3
    retry_delay = 30  # seconds
    fetch_success = False
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Running Dune Fetcher (attempt {attempt}/{max_retries})...")
            await fetcher.run()
            fetch_success = True
            logger.info("Dune Fetcher completed successfully.")
            break
        except Exception as e:
            logger.error(f"Dune Fetcher failed on attempt {attempt}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying Fetcher in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                
    if not fetch_success:
        logger.error("Dune Fetcher failed after all attempts. Skipping Scoring Engine for this hour.")
        return

    # 2. Generate hourly AI recommendations for the dashboard
    try:
        logger.info("Running Dashboard AI Picks Generator...")
        recent_yields = await scorer.ai.get_recent_yields()
        if recent_yields:
            await scorer.ai.generate_dashboard_picks(recent_yields)
            logger.info("Dashboard AI Picks generated successfully.")
        else:
            logger.warning("No recent yields found. Skipping AI picks generation.")
    except Exception as e:
        logger.error(f"Dashboard AI Picks Generator failed with exception: {e}")

    # 3. Run Scorer to evaluate paper trades against updated yields and queue alerts
    try:
        logger.info("Running Hourly AI Scoring Engine...")
        await scorer.run()
        logger.info("Hourly AI Scoring Engine completed successfully.")
    except Exception as e:
        logger.error(f"Hourly Scoring Engine failed with exception: {e}")

async def retry_failed_onchain_logs():
    """
    Finds recommendations that were hashed but not yet logged on-chain,
    and retries the transaction. Runs every 6 hours.
    """
    from logger import log_recommendation_onchain, hash_payload, build_recommendation_payload
    from datetime import datetime, timezone

    if not supabase:
        logger.error("[retry_job] Supabase client not initialized.")
        return

    try:
        result = supabase.table("recommendations") \
            .select("*") \
            .is_("on_chain_tx_hash", "null") \
            .not_.is_("recommendation_hash", "null") \
            .execute()
        pending = result.data
    except Exception as e:
        logger.error(f"[retry_job] Failed to fetch pending recommendations: {e}")
        return

    if not pending:
        logger.info("[retry_job] No pending on-chain logs. All clear.")
        return

    logger.info(f"[retry_job] Found {len(pending)} recommendations missing tx_hash. Retrying...")
    for rec in pending:
        try:
            # Reconstruct the payload from the DB row
            protocol_res = supabase.table("protocols") \
                .select("name, pool_name, pool_address") \
                .eq("id", rec["protocol_id"]) \
                .single() \
                .execute()
            protocol = protocol_res.data
            if not protocol:
                logger.error(f"[retry_job] Protocol id {rec['protocol_id']} not found. Skipping.")
                continue

            payload = build_recommendation_payload(
                protocol_name = protocol["name"],
                pool_name     = protocol["pool_name"],
                pool_address  = protocol["pool_address"],
                risk_tag      = rec["risk_tag"],
                rank          = rec["rank"],
                apy_at_time   = rec["apy_at_time"],
                tvl_usd       = 0.0,          # TVL not stored in rec — use 0.0 as placeholder
                ai_reasoning  = rec["ai_reasoning"],
                ai_model      = rec["ai_model"],
                scored_at     = datetime.fromisoformat(rec["created_at"].replace("Z", "+00:00")),
            )

            # Verify the hash still matches before sending the transaction
            recomputed_hash = hash_payload(payload)
            if recomputed_hash != rec["recommendation_hash"]:
                logger.error(
                    f"[retry_job] Hash mismatch for rec {rec['id']}! "
                    f"Stored: {rec['recommendation_hash'][:12]} | "
                    f"Recomputed: {recomputed_hash[:12]}. Skipping."
                )
                continue

            tx_hash, _ = log_recommendation_onchain(payload, max_retries=2)
            if tx_hash:
                supabase.table("recommendations").update({
                    "on_chain_tx_hash":   tx_hash,
                    "on_chain_logged_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", rec["id"]).execute()
                logger.info(f"[retry_job] ✅ Recovered rec {rec['id']}: {tx_hash}")
        except Exception as e:
            logger.error(f"[retry_job] Error retrying rec {rec.get('id')}: {e}")

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # Run immediately on startup, then every 1 hour
    scheduler.add_job(run_pipeline, 'interval', hours=1, id="pipeline_job", next_run_time=datetime.now())
    
    # Run retry job every 6 hours
    scheduler.add_job(
        retry_failed_onchain_logs,
        "interval",
        hours=6,
        id="retry_onchain_logs",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("APScheduler started. Pipeline job running now, then every 1 hour. Retry job runs every 6 hours.")
    
    # Keep the main thread alive if run independently
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    start_scheduler()
