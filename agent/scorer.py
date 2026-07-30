import asyncio
import logging
import json
from datetime import datetime, timezone
from ai_service import AIService
from fetcher import supabase
from logger import (
    build_recommendation_payload,
    log_recommendation_solana,
    get_solscan_url,
)

logger = logging.getLogger(__name__)

class HourlyScorer:
    def __init__(self):
        self.ai = AIService()

    async def generate_and_store_recommendations(self, yields):
        """
        Generates global dashboard picks per risk tier, stores them in Supabase,
        hashes them, and anchors them on Solana via SPL Memo.
        """
        logger.info("Generating global Solana yield recommendations for dashboard...")
        scored_at = datetime.now(timezone.utc)

        risk_tiers = ["stable", "moderate", "aggressive"]
        for risk in risk_tiers:
            try:
                # Filter yields matching risk tier roughly or pass all to LLM for ranking
                filtered_yields = [y for y in yields if (y.get("protocols") or {}).get("risk_tag") == risk]
                target_yields = filtered_yields if len(filtered_yields) >= 3 else yields

                top_picks = await self.ai.generate_hourly_analysis(target_yields)
                if not top_picks or not isinstance(top_picks, list):
                    continue

                for rank, pick in enumerate(top_picks[:3], start=1):
                    protocol_id = pick.get("protocol_id")
                    if not protocol_id:
                        continue

                    apy_at_time = float(pick.get("apy") or pick.get("APY") or 0.0)
                    tvl_usd = float(pick.get("tvl_usd") or pick.get("TVL ($)") or 0.0)
                    reasoning = pick.get("reasoning") or pick.get("ai_reasoning") or "Strong risk-adjusted yield."
                    model_used = pick.get("model_used") or "meta/llama-3.3-70b-instruct"

                    # 1. Insert recommendation row into Supabase
                    rec_payload = {
                        "protocol_id": protocol_id,
                        "risk_tag": risk,
                        "rank": rank,
                        "apy_at_time": apy_at_time,
                        "tvl_usd_at_time": tvl_usd,
                        "ai_reasoning": reasoning,
                        "ai_model": model_used,
                        "recommendation_hash": "pending",
                        "created_at": scored_at.isoformat(),
                    }

                    insert_res = supabase.table("recommendations").insert(rec_payload).execute()
                    if not insert_res.data:
                        continue
                    rec_id = insert_res.data[0]["id"]

                    # 2. Build canonical payload for hashing
                    protocol_name = pick.get("protocol_name") or pick.get("name") or "Solana Protocol"
                    pool_name = pick.get("pool_name") or pick.get("asset") or "SOL Pool"
                    program_address = pick.get("program_address") or pick.get("pool_address") or ""

                    payload = build_recommendation_payload(
                        protocol_name=protocol_name,
                        pool_name=pool_name,
                        program_address=program_address,
                        risk_tag=risk,
                        rank=rank,
                        apy_at_time=apy_at_time,
                        tvl_usd=tvl_usd,
                        ai_reasoning=reasoning,
                        ai_model=model_used,
                        scored_at=scored_at,
                    )

                    # 3. Anchor recommendation on Solana
                    tx_signature, rec_hash = log_recommendation_solana(payload)

                    # 4. Update row with rec_hash and tx_signature
                    update_data = {"recommendation_hash": rec_hash}
                    if tx_signature:
                        update_data["on_chain_tx_signature"] = tx_signature
                        update_data["on_chain_logged_at"] = datetime.now(timezone.utc).isoformat()

                    supabase.table("recommendations").update(update_data).eq("id", rec_id).execute()
                    logger.info(f"Logged recommendation {rec_id} for {protocol_name} on Solana (sig: {tx_signature or 'pending'})")

            except Exception as e:
                logger.error(f"Error processing recommendations for risk tier {risk}: {e}")

    async def run(self):
        logger.info("Starting Hourly AI Scoring Engine & Personalized Alerts...")
        if not supabase:
            logger.error("Supabase client not initialized. Skipping scorer.")
            return

        # 1. Fetch latest yields
        yields = await self.ai.get_recent_yields()
        if not yields:
            logger.warning("No live yields found. Skipping hourly updates.")
            return

        # 2. Generate and anchor global dashboard recommendations
        try:
            await self.generate_and_store_recommendations(yields)
        except Exception as e:
            logger.error(f"Error during global recommendation generation: {e}")

        # 3. Get all users
        try:
            users_res = supabase.table("users").select("id, telegram_chat_id, risk_preference").execute()
            users = users_res.data
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            return

        if not users:
            logger.info("No registered users found. Skipping personalized alerts.")
            return

        # 4. Get alert preferences
        try:
            pref_res = supabase.table("alert_preferences").select("user_id, is_active").execute()
            pref_map = {p["user_id"]: p["is_active"] for p in pref_res.data}
        except Exception as e:
            logger.error(f"Error fetching alert preferences: {e}")
            pref_map = {}

        # 5. Fetch active paper trades
        try:
            trades_res = supabase.table("paper_trades")\
                .select("*, protocols(*)")\
                .eq("status", "active")\
                .execute()
            all_trades = trades_res.data
        except Exception as e:
            logger.error(f"Error fetching active paper trades: {e}")
            all_trades = []

        user_trades_map = {}
        for t in all_trades:
            uid = t["user_id"]
            if uid not in user_trades_map:
                user_trades_map[uid] = []
            user_trades_map[uid].append(t)

        # 6. Process users sequentially
        async def process_user(user):
            user_id = user["id"]
            chat_id = user["telegram_chat_id"]
            risk_preference = user.get("risk_preference") or "stable,moderate,aggressive"

            if not chat_id:
                return

            is_active = pref_map.get(user_id)
            if is_active is None:
                is_active = True
                try:
                    supabase.table("alert_preferences").insert({"user_id": user_id, "is_active": True}).execute()
                except Exception as ap_err:
                    logger.error(f"Error provisioning alert preferences row for user {user_id}: {ap_err}")

            if not is_active:
                logger.info(f"User {user_id} has disabled alerts. Skipping.")
                return

            user_trades = user_trades_map.get(user_id, [])
            logger.info(f"Generating personalized hourly update for user {user_id} ({len(user_trades)} active trades, risk: {risk_preference})...")

            try:
                update_msg = await self.ai.generate_personalized_hourly_update(
                    risk_preference=risk_preference,
                    user_trades=user_trades,
                    yields=yields,
                    user_id=user_id,
                )

                payload = {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "message_type": "alert",
                    "content": update_msg,
                    "status": "pending"
                }
                supabase.table("telegram_messages").insert(payload).execute()
                logger.info(f"Successfully queued hourly DeFi update for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to generate/queue update for user {user_id}: {e}")

        for i, user in enumerate(users):
            await process_user(user)
            if i < len(users) - 1:
                await asyncio.sleep(3)

if __name__ == "__main__":
    scorer = HourlyScorer()
    asyncio.run(scorer.run())

