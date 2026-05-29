import asyncio
import logging
import json
from ai_service import AIService
from fetcher import supabase

logger = logging.getLogger(__name__)

class HourlyScorer:
    def __init__(self):
        self.ai = AIService()

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

        # 2. Get all users
        try:
            users_res = supabase.table("users").select("id, telegram_chat_id, risk_preference").execute()
            users = users_res.data
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            return

        if not users:
            logger.info("No registered users found. Skipping scorer.")
            return

        # 3. Get all alert preferences to filter enabled users
        try:
            pref_res = supabase.table("alert_preferences").select("user_id, is_active").execute()
            pref_map = {p["user_id"]: p["is_active"] for p in pref_res.data}
        except Exception as e:
            logger.error(f"Error fetching alert preferences: {e}")
            pref_map = {}

        # 4. Fetch all active paper trades at once to group them by user
        try:
            trades_res = supabase.table("paper_trades")\
                .select("*, protocols(*)")\
                .eq("status", "active")\
                .execute()
            all_trades = trades_res.data
        except Exception as e:
            logger.error(f"Error fetching active paper trades: {e}")
            all_trades = []

        # Group trades by user_id
        user_trades_map = {}
        for t in all_trades:
            uid = t["user_id"]
            if uid not in user_trades_map:
                user_trades_map[uid] = []
            user_trades_map[uid].append(t)

        # 5. Process each user
        for user in users:
            user_id = user["id"]
            chat_id = user["telegram_chat_id"]
            risk_preference = user.get("risk_preference") or "stable,moderate,aggressive"

            if not chat_id:
                continue

            # Resolve alerts opt-in status (default to True if not in database)
            is_active = pref_map.get(user_id)
            if is_active is None:
                is_active = True
                # Dynamically provision missing preference row for existing users
                try:
                    supabase.table("alert_preferences").insert({"user_id": user_id, "is_active": True}).execute()
                except Exception as ap_err:
                    logger.error(f"Error provisioning alert preferences row for user {user_id}: {ap_err}")

            if not is_active:
                logger.info(f"User {user_id} has disabled alerts. Skipping.")
                continue

            user_trades = user_trades_map.get(user_id, [])
            logger.info(f"Generating personalized hourly update for user {user_id} ({len(user_trades)} active trades, risk: {risk_preference})...")

            try:
                # Generate highly intelligent personalized update ( Sonnet 4.6 )
                update_msg = await self.ai.generate_personalized_hourly_update(
                    risk_preference=risk_preference,
                    user_trades=user_trades,
                    yields=yields
                )

                # Queue the Telegram message
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

if __name__ == "__main__":
    scorer = HourlyScorer()
    asyncio.run(scorer.run())
