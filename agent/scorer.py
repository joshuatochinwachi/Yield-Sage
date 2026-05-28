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
        logger.info("Starting Hourly AI Scoring Engine...")
        
        # 1. Get latest yields and active paper trades
        yields = await self.ai.get_recent_yields()
        trades = await self.ai.get_user_paper_trades()
        
        if not trades:
            logger.info("No active paper trades found. Skipping hourly alerts.")
            return

        # 2. Ask Claude to analyze the trades against the new yields
        alerts = await self.ai.generate_hourly_analysis(yields, trades)
        
        if not alerts:
            logger.info("Claude returned no alerts for this hour.")
            return

        logger.info(f"Generated {len(alerts)} alerts. Saving to DB...")

        # 3. Store alerts in DB (or trigger push directly)
        # We will store them in telegram_messages to be picked up by the bot
        for alert in alerts:
            user_id = alert.get("user_id")
            message = alert.get("alert_message")
            
            if user_id and message and supabase:
                try:
                    # Look up user's telegram_chat_id
                    res = supabase.table("users").select("telegram_chat_id").eq("id", user_id).limit(1).execute()
                    if res.data and res.data[0].get("telegram_chat_id"):
                        chat_id = res.data[0]["telegram_chat_id"]
                        
                        payload = {
                            "user_id": user_id,
                            "chat_id": chat_id,
                            "message_type": "alert",
                            "content": f"🚨 **Yield Alert on your Paper Trade** 🚨\n\n{message}",
                            "status": "pending"
                        }
                        supabase.table("telegram_messages").insert(payload).execute()
                        logger.info(f"Queued alert for user {user_id}")
                except Exception as e:
                    logger.error(f"Error queueing alert: {e}")

if __name__ == "__main__":
    scorer = HourlyScorer()
    asyncio.run(scorer.run())
