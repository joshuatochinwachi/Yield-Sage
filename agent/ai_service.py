import os
import json
import logging
from datetime import datetime
from supabase import create_client, Client
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# Anthropic setup
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if ANTHROPIC_API_KEY:
    anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
else:
    anthropic = None

class AIService:
    def __init__(self):
        self.haiku_model = "claude-3-haiku-20240307"
        self.sonnet_model = "claude-3-5-sonnet-20241022"

    async def get_recent_yields(self):
        """Fetch the latest snapshot for each active protocol."""
        if not supabase: return []
        try:
            # First get active protocols
            protocols_res = supabase.table("protocols").select("id, name, pool_name, risk_tag").eq("is_active", True).execute()
            protocols = protocols_res.data
            
            latest_yields = []
            for p in protocols:
                snap_res = supabase.table("yield_snapshots").select("*").eq("protocol_id", p["id"]).order("fetched_at", desc=True).limit(1).execute()
                if snap_res.data:
                    yield_data = snap_res.data[0]
                    yield_data["protocol"] = p
                    latest_yields.append(yield_data)
            return latest_yields
        except Exception as e:
            logger.error(f"Error fetching recent yields: {e}")
            return []

    async def get_user_paper_trades(self, user_id: str = None, telegram_chat_id: int = None):
        """Fetch active paper trades for a user, or all active trades if no user is specified."""
        if not supabase: return []
        try:
            query = supabase.table("paper_trades").select("*, protocols(name, pool_name)").eq("status", "active")
            
            # If user filters are specified, resolve and filter by user
            if user_id or telegram_chat_id:
                user_uuid = await self._resolve_user(user_id, telegram_chat_id)
                if not user_uuid: return []
                query = query.eq("user_id", user_uuid)
                
            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching paper trades: {e}")
            return []

    async def _resolve_user(self, user_id: str = None, telegram_chat_id: int = None):
        """Resolve a telegram_chat_id to a Supabase user_id if needed."""
        if user_id: return user_id
        if not telegram_chat_id or not supabase: return None
        try:
            res = supabase.table("users").select("id").eq("telegram_chat_id", telegram_chat_id).limit(1).execute()
            if res.data:
                return res.data[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Error resolving user: {e}")
            return None

    async def load_chat_memory(self, user_id: str = None, telegram_chat_id: int = None, limit: int = 15):
        """Load recent conversation history."""
        if not supabase: return []
        try:
            query = supabase.table("chat_memory").select("role, content").order("created_at", desc=True).limit(limit)
            user_uuid = await self._resolve_user(user_id, telegram_chat_id)
            
            if user_uuid:
                query = query.eq("user_id", user_uuid)
            elif telegram_chat_id:
                query = query.eq("telegram_chat_id", telegram_chat_id)
            else:
                return []
                
            res = query.execute()
            # Reverse to chronological order
            return [{"role": r["role"], "content": r["content"]} for r in reversed(res.data)]
        except Exception as e:
            logger.error(f"Error loading chat memory: {e}")
            return []

    async def push_to_memory(self, role: str, content: str, user_id: str = None, telegram_chat_id: int = None):
        """Save a message to conversation history."""
        if not supabase: return
        try:
            user_uuid = await self._resolve_user(user_id, telegram_chat_id)
            payload = {
                "role": role,
                "content": content
            }
            if user_uuid:
                payload["user_id"] = user_uuid
            if telegram_chat_id:
                payload["telegram_chat_id"] = telegram_chat_id
                
            supabase.table("chat_memory").insert(payload).execute()
        except Exception as e:
            logger.error(f"Error pushing to memory: {e}")

    async def handle_conversational_query(self, user_message: str, user_id: str = None, telegram_chat_id: int = None):
        """Main entrypoint for Telegram bot chats. Uses Haiku for speed/cost."""
        if not anthropic:
            return "AI service is currently unconfigured. Please check API keys."
            
        # 1. Save user message
        await self.push_to_memory("user", user_message, user_id, telegram_chat_id)
        
        # 2. Gather context
        history = await self.load_chat_memory(user_id, telegram_chat_id, limit=10)
        yields = await self.get_recent_yields()
        paper_trades = await self.get_user_paper_trades(user_id, telegram_chat_id)
        
        # Format context tightly
        yield_context = "Current Live Yields (Mantle Network):\n"
        for y in yields:
            p = y["protocol"]
            apy_val = y.get("apy")
            apy_str = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            risk_tag = p.get('risk_tag') or 'unknown'
            yield_context += f"- {p['name']} ({p['pool_name']}): {apy_str} APY (Risk: {risk_tag.upper()})\n"
            
        trade_context = "User's Active Paper Trades:\n"
        if paper_trades:
            for t in paper_trades:
                p = t["protocols"]
                trade_context += f"- ${t['simulated_investment_usd']} in {p['name']} ({p['pool_name']}) at {t['entry_apy']}% APY.\n"
        else:
            trade_context += "- None active.\n"
            
        system_prompt = f"""You are YieldSage, an intelligent DeFi advisor on the Mantle network.
Your goal is to help users find the best yields, simulate trades (paper trading), and adjust their positions based on market changes.
Keep your answers concise, friendly, and analytical. Use formatting (bolding, lists) to make it readable.
If the user wants to start a paper trade, instruct them to use the `/paper_trade` command.

CONTEXT INJECTION:
{yield_context}
{trade_context}
"""

        # Construct Anthropic messages
        # History already contains the latest user message because we just pushed it,
        # but we need to pass it properly to the Anthropic API.
        
        # Filter out 'system' roles from history if any snuck in, as Anthropic only accepts user/assistant in messages array
        valid_history = [msg for msg in history if msg["role"] in ["user", "assistant"]]
        
        try:
            response = await anthropic.messages.create(
                model=self.haiku_model,
                max_tokens=1000,
                system=system_prompt,
                messages=valid_history,
                temperature=0.3
            )
            
            bot_reply = response.content[0].text
            
            # 3. Save assistant message
            await self.push_to_memory("assistant", bot_reply, user_id, telegram_chat_id)
            
            return bot_reply
            
        except Exception as e:
            logger.error(f"Claude API Error: {e}")
            return "Sorry, I'm having trouble analyzing the market right now. Please try again in a moment."

    async def generate_hourly_analysis(self, yields, paper_trades):
        """Used by the Scorer to evaluate positions and generate alerts. Uses Sonnet 3.5."""
        if not anthropic: return []
        
        yield_context = "Latest Yield Snapshots:\n"
        for y in yields:
            p = y.get("protocol", {})
            yield_context += f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): {y.get('apy', 0):.2f}% APY (Risk: {p.get('risk_tag', 'Unknown').upper()})\n"
            
        trade_context = "Active Paper Trades to Evaluate:\n"
        for t in paper_trades:
            p = t.get("protocols", {})
            trade_context += f"Trade ID: {t['id']} | User ID: {t['user_id']} | Protocol: {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}) | Entry APY: {t['entry_apy']}% | Current Investment: ${t['simulated_investment_usd']}\n"
            
        system_prompt = """You are YieldSage's backend scoring engine.
Analyze the provided paper trades against the latest yield data. 
Identify any trades that are significantly underperforming compared to better opportunities in the SAME risk tier.
If a trade is underperforming by more than 2% APY compared to an alternative, generate an alert.

Return ONLY a strict JSON array of alerts (no markdown formatting, no preamble). Example:
[
  {
    "user_id": "uuid",
    "trade_id": "uuid",
    "alert_message": "Your paper trade on Agni USDC/USDT has dropped to 8% APY. Consider moving to Merchant Moe USDC/USDT for 12.5% APY."
  }
]
If no alerts are needed, return an empty array: []
"""

        try:
            response = await anthropic.messages.create(
                model=self.sonnet_model,
                max_tokens=1500,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Yields:\n{yield_context}\n\nTrades:\n{trade_context}\n\nAnalyze and return JSON."}
                ],
                temperature=0.1
            )
            
            # Parse JSON
            content = response.content[0].text.strip()
            # Strip potential markdown block
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"Error in hourly analysis: {e}")
            return []
