import os
import re
import json
import logging
import httpx
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

def clean_pool_url(pool_address) -> str | None:
    if not pool_address:
        return None
    s = str(pool_address).strip()
    s_lower = s.lower()
    _BAD = {"nan", "none", "null", "n/a", "", "undefined"}
    if s_lower in _BAD:
        return None
    if any(s_lower.endswith(f"/{b}") for b in _BAD):
        return None
    if s_lower.startswith("http://") or s_lower.startswith("https://"):
        return s
    return f"https://solscan.io/account/{s}"


def enforce_authentic_pool_links(text: str, allowed_pool_url_map: dict) -> str:
    """
    Post-processing guard: strips any Markdown link whose URL is not in the
    authenticated allowed_pool_url_map built from live DB data.
    System links (yieldsageai.xyz, t.me) are always preserved.
    """
    if not text:
        return text
    SYSTEM_PATTERNS = ["yieldsageai.xyz/verify", "yield.hollowscan.com/verify", "yieldsageai.xyz/dashboard", "yield.hollowscan.com/dashboard", "t.me/YieldSageBot"]

    def _validate_link(match):
        label = match.group(1).strip()
        url = match.group(2).strip()
        if any(sys_pat in url for sys_pat in SYSTEM_PATTERNS):
            return f"[{label}]({url})"
        label_clean = re.sub(r'^[•\-\*\s]+', '', label).strip().lower()
        matched_url = None
        for pool_key, valid_url in allowed_pool_url_map.items():
            if valid_url and (pool_key in label_clean or label_clean in pool_key):
                matched_url = valid_url
                break
        if matched_url and url.lower() == matched_url.lower():
            return f"[{label}]({url})"
        all_valid_urls = {v.lower() for v in allowed_pool_url_map.values() if v}
        if url.lower() in all_valid_urls:
            return f"[{label}]({url})"
        logger.warning(f"[URL Guard] Stripped unverified link for '{label}': {url}")
        return label

    return re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', _validate_link, text)

def clean_telegram_markdown(text: str) -> str:
    if not text:
        return ""
    
    # 0. Strip spaces/newlines immediately inside link parenthesis, then merge split markdown links
    text = re.sub(r'\(\s+(https?://)', r'(\1', text)
    text = re.sub(r'\]\s*\(https?://', '](https://', text)
    
    # 0b. Convert any /paper_trade commands to /trade
    text = text.replace("/paper_trade", "/trade").replace("/paper\\_trade", "/trade").replace("/paper\\\\_trade", "/trade")
    
    # 0c. PERMANENT FIX: Transform [Protocol (Pool)](url) → [Protocol](url) (Pool)
    def to_yields_style_link(match):
        full_text = match.group(1).strip().strip("*")
        url = match.group(2).strip()

        _BAD_ADDR = {"nan", "none", "null", "n/a", "", "undefined"}
        u_lower = url.lower()
        if (
            any(u_lower.endswith(f"/{b}") for b in _BAD_ADDR)
            or u_lower in _BAD_ADDR
            or any(f"/{b}?" in u_lower for b in _BAD_ADDR)
        ):
            protocol = full_text
            pool = ""
            for sep in [" (", " -> ", " ➛ ", " - "]:
                if sep in full_text:
                    pts = full_text.split(sep, 1)
                    protocol = pts[0].strip()
                    pool = pts[1].strip()
                    if pool.endswith(")"):
                        pool = pool[:-1].strip()
                    break
            return f"{protocol} ({pool})" if pool else f"{protocol}"

        protocol = full_text
        pool = ""
        for sep in [" (", " -> ", " ➛ ", " - "]:
            if sep in full_text:
                pts = full_text.split(sep, 1)
                protocol = pts[0].strip()
                pool = pts[1].strip()
                if pool.endswith(")"):
                    pool = pool[:-1].strip()
                break
        return f"[{protocol}]({url}) ({pool})" if pool else f"[{protocol}]({url})"

    text = re.sub(r'\[([^\]]+)\]\((https://[^)]+)\)', to_yields_style_link, text)
    # This EXACTLY mirrors the /yields command format which renders perfectly on all clients.
    # Link text is ONLY the protocol name (no special chars), pool name is plain text outside brackets.
    def to_yields_style_link(match):
        full_text = match.group(1).strip()
        url = match.group(2).strip()
        
        protocol = full_text
        pool = ""
        
        # Safely extract Protocol and Pool by checking common separators from the AI
        for sep in [" (", " -> ", " ➛ ", " - "]:
            if sep in full_text:
                parts = full_text.split(sep, 1)
                protocol = parts[0].strip()
                pool = parts[1].strip()
                if pool.endswith(")"):
                    pool = pool[:-1].strip()
                break
                
        if pool:
            return f"[{protocol}]({url}) ({pool})"
        else:
            return f"[{protocol}]({url})"
    
    text = re.sub(r'\[([^\]]+)\]\((https://[^)]+)\)', to_yields_style_link, text)
    
    # 1. Replace double asterisks with single asterisks for bold
    text = text.replace("**", "*")
    
    # 2. Process line by line
    lines = text.split("\n")
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Convert Markdown headers to bold
        if stripped.startswith("#"):
            hashes = 0
            for char in stripped:
                if char == "#":
                    hashes += 1
                else:
                    break
            header_content = stripped[hashes:].strip()
            line = f"*{header_content}*"
            
        # Convert horizontal rules to blank lines
        elif stripped in ["---", "===", "___", "***"]:
            line = ""
            
        cleaned_lines.append(line)
        
    text = "\n".join(cleaned_lines)
    
    # 3. Escape underscores except when part of a URL, telegram command, or already escaped.
    pattern = re.compile(r'(https?://[^\s\)]+|/\w+|\\_)')
    parts = []
    last_idx = 0
    for match in pattern.finditer(text):
        start, end = match.span()
        parts.append(text[last_idx:start].replace("_", "\\_"))
        parts.append(text[start:end])
        last_idx = end
    parts.append(text[last_idx:].replace("_", "\\_"))
    
    return "".join(parts)

class AIService:
    def __init__(self):
        self.haiku_model = "claude-haiku-4-5-20251001"
        self.sonnet_model = "claude-sonnet-4-6"

    async def get_recent_yields(self):
        """Fetch the latest snapshot for each active protocol using range pagination past PostgREST 1000 limit."""
        if not supabase:
            return []
        try:
            all_snapshots = []
            step = 1000
            start = 0
            while True:
                snap_res = supabase.table("yield_snapshots").select(
                    "*, protocols!inner(id, name, pool_name, pool_address, risk_tag, is_active)"
                ).eq("protocols.is_active", True).order(
                    "fetched_at", desc=True
                ).range(start, start + step - 1).execute()

                batch = snap_res.data or []
                all_snapshots.extend(batch)
                if len(batch) < step:
                    break
                start += step

            seen = set()
            latest_yields = []
            for row in all_snapshots:
                proto = row.get("protocols") or {}
                pid = row.get("protocol_id") or proto.get("id")
                if pid and pid not in seen:
                    seen.add(pid)
                    latest_yields.append({
                        **row,
                        "protocol": proto,
                    })

            return latest_yields
        except Exception as e:
            logger.error(f"Error fetching recent yields: {e}")
            return []

    async def get_user_paper_trades(self, user_id: str = None, telegram_chat_id: int = None):
        """Fetch active paper trades for a user, or all active trades if no user is specified."""
        if not supabase: return []
        try:
            query = supabase.table("paper_trades").select("*, protocols(name, pool_name, pool_address)").eq("status", "active")
            
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

    async def search_web(self, query: str) -> str:
        """Performs a web search via DuckDuckGo HTML endpoint and returns structured snippet results."""
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data={"q": query}, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"DDG Search HTTP error {resp.status_code}")
                    return ""
                
                text = resp.text
                # Use regex to find snippets and titles
                snippets = re.findall(r'class="[^"]*snippet[^"]*"[^>]*>(.*?)</', text, re.DOTALL)
                titles = re.findall(r'class="[^"]*result__link[^"]*"[^>]*>(.*?)</', text, re.DOTALL)
                if not titles:
                    titles = re.findall(r'class="[^"]*result-link[^"]*"[^>]*>(.*?)</', text, re.DOTALL)
                    
                results = []
                import html
                clean_tags = re.compile('<.*?>')
                
                for i in range(min(len(snippets), len(titles), 5)):
                    title_clean = re.sub(clean_tags, '', titles[i]).strip()
                    snippet_clean = re.sub(clean_tags, '', snippets[i]).strip()
                    title_clean = html.unescape(title_clean)
                    snippet_clean = html.unescape(snippet_clean)
                    if title_clean and snippet_clean:
                        results.append(f"• **{title_clean}**\n  {snippet_clean}")
                        
                if not results:
                    # Generic fallback to any matching snippets if title pairing failed
                    for s in snippets[:5]:
                        snippet_clean = re.sub(clean_tags, '', s).strip()
                        snippet_clean = html.unescape(snippet_clean)
                        if snippet_clean:
                            results.append(f"• {snippet_clean}")
                
                return "\n\n".join(results)
        except Exception as e:
            logger.error(f"Search Web Error: {e}")
            return ""

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
        allowed_pool_url_map = {}
        yield_context = "Current Live Yields (Solana Ecosystem):\n"
        for y in yields:
            p = y["protocol"]
            apy_val = y.get("apy")
            apy_str = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            risk_tag = p.get('risk_tag') or 'unknown'
            url = clean_pool_url(p.get('pool_address'))
            if url:
                name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                allowed_pool_url_map[name_key] = url
                if p.get('name'):
                    allowed_pool_url_map[p.get('name').lower()] = url
                yield_context += f"- [{p['name']} ({p['pool_name']})]({url}): {apy_str} APY (Risk: {risk_tag.upper()})\n"
            else:
                yield_context += f"- {p['name']} ({p['pool_name']}): {apy_str} APY (Risk: {risk_tag.upper()})\n"

        trade_context = "User's Active Paper Trades:\n"
        if paper_trades:
            for t in paper_trades:
                p = t["protocols"]
                t_url = clean_pool_url(p.get('pool_address'))
                if t_url:
                    t_name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                    allowed_pool_url_map[t_name_key] = t_url
                    if p.get('name'):
                        allowed_pool_url_map[p.get('name').lower()] = t_url
                trade_context += f"- ${t['simulated_investment_usd']} in {p['name']} ({p['pool_name']}) at {t['entry_apy']}% APY.\n"
        else:
            trade_context += "- None active.\n"
            
        system_prompt = f"""You are YieldSage, a premium, autonomous DeFi advisor on Solana.
Your goal is to help users find the best yields, simulate trades (paper trading), and adjust their positions based on market changes.
Keep your answers concise, friendly, and analytical. Use formatting (bolding, lists) to make it readable.
If the user wants to start a paper trade, instruct them to use the `/trade` command.
Whenever you mention, recommend, list, or refer to any yield pool that has an EXACT address link in the context below, you MUST copy that link exactly to format the pool name as a Markdown link (e.g. `[Protocol - Pool](exact_url_from_context)`). If no address/link is in the context for a pool, write its name as plain text — never invent or construct a URL.

CRITICAL FORMATTING RULES FOR TELEGRAM:
1. NO HEADERS: Do not use #, ##, or ###. Instead, bold your section titles like this: **Section Title**
2. NO TABLES: Do not use Markdown tables (e.g. | column | column |). Instead, use bullet points.
3. NO DIVIDERS: Do not use horizontal rules (---). Use blank lines to separate sections.
4. LINKS: Use inline links [text](url). Use double asterisks for bold **text**.

CONTEXT INJECTION:
{yield_context}
{trade_context}
"""

        # Construct Anthropic messages
        # History already contains the latest user message because we just pushed it,
        # but we need to pass it properly to the Anthropic API.
        
        # Filter out 'system' roles from history if any snuck in, as Anthropic only accepts user/assistant in messages array
        valid_history = [msg for msg in history if msg["role"] in ["user", "assistant"]]
        
        # Anthropic STRICTLY requires alternating roles (user, assistant, user). 
        # If the user sent 2 messages in a row before the bot replied, it will crash.
        compressed_history = []
        for msg in valid_history:
            if not compressed_history:
                compressed_history.append(msg)
            elif compressed_history[-1]["role"] == msg["role"]:
                compressed_history[-1]["content"] += "\n" + msg["content"]
            else:
                compressed_history.append(msg)
                
        # Anthropic requires the first message to be 'user'. Drop if it's 'assistant'.
        if compressed_history and compressed_history[0]["role"] == "assistant":
            compressed_history.pop(0)
        
        try:
            tools = [
                {
                    "name": "search_web",
                    "description": "Searches the web for real-time information, news, general facts, or DeFi topics outside our database.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to run."
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]

            response = await anthropic.messages.create(
                model=self.haiku_model,
                max_tokens=1500,
                system=system_prompt,
                messages=compressed_history,
                tools=tools,
                temperature=0.3
            )
            
            # Check if model wants to run a tool
            if response.stop_reason == "tool_use":
                tool_uses = [block for block in response.content if block.type == "tool_use"]
                
                tool_results = []
                for tool_use in tool_uses:
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    tool_use_id = tool_use.id
                    
                    if tool_name == "search_web":
                        query_val = tool_input.get("query")
                        logger.info(f"Claude Haiku requested search_web for: '{query_val}'")
                        
                        # Execute search
                        search_results = await self.search_web(query_val)
                        if not search_results:
                            search_results = "No search results found."
                            
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"Web Search Results for '{query_val}':\n\n{search_results}"
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"Error: unknown tool {tool_name}"
                        })
                        
                # Build history update for Claude
                assistant_msg = {
                    "role": "assistant",
                    "content": response.content
                }
                tool_result_msg = {
                    "role": "user",
                    "content": tool_results
                }
                
                # Final response from Claude with the search results included
                final_response = await anthropic.messages.create(
                    model=self.haiku_model,
                    max_tokens=1500,
                    system=system_prompt,
                    messages=compressed_history + [assistant_msg, tool_result_msg],
                    tools=tools,
                    temperature=0.3
                )
                bot_reply = final_response.content[0].text
            else:
                bot_reply = response.content[0].text

            # Strip hallucinated or unregistered links before markdown cleaning
            bot_reply = enforce_authentic_pool_links(bot_reply, allowed_pool_url_map)
            bot_reply = clean_telegram_markdown(bot_reply)

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
            apy_val = y.get("apy")
            apy_str = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            risk_tag = p.get('risk_tag') or 'unknown'
            yield_context += f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): {apy_str} APY (Risk: {risk_tag.upper()})\n"
            
        trade_context = "Active Paper Trades to Evaluate:\n"
        for t in paper_trades:
            p = t.get("protocols", {})
            trade_context += f"Trade ID: {t['id']} | User ID: {t['user_id']} | Protocol: {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}) | Entry APY: {t['entry_apy']}% | Current Investment: ${t['simulated_investment_usd']}\n"
            
        system_prompt = """You are YieldSage's backend scoring engine.
Analyze the provided paper trades against the latest yield data.
Generate a brief hourly status update for each trade.
If a trade is underperforming by more than 2% APY compared to a better opportunity in the SAME risk tier, highlight it as an ALERT and recommend the better pool.
If the trade is performing well, just provide a reassuring status update (e.g., 'Your trade on X is currently earning Y%.').

Return ONLY a strict JSON array of messages (no markdown formatting, no preamble). Example:
[
  {
    "user_id": "uuid",
    "trade_id": "uuid",
    "alert_message": "Hourly Update: Your paper trade on Kamino is earning 5% APY. Looks solid — no better alternative at this risk tier right now."
  }
]
You MUST generate an update for EVERY active trade. Do not return an empty array if trades exist.
Do not use underscores (_) in pool names to prevent Telegram formatting errors.
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

    async def generate_personalized_hourly_update(self, risk_preference: str, user_trades: list, yields: list) -> str:
        """Generates a personalized hourly Telegram message for a user, containing recommendations, yield info, position shifts, and insights."""
        if not anthropic:
            return "⚠️ YieldSage background services are temporarily offline. Please check back later."

        # Build authoritative URL map for post-processing
        allowed_pool_url_map: dict = {}
        yield_context = ""
        for y in yields:
            p = y.get("protocol", {})
            apy_val = y.get("apy")
            apy_str = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            risk_tag = p.get('risk_tag') or 'unknown'
            tvl_val = y.get('tvl_usd') or 0
            tvl_str = f"${tvl_val:,.0f}" if tvl_val else "N/A"
            url = clean_pool_url(p.get('pool_address'))
            if url:
                name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                allowed_pool_url_map[name_key] = url
                if p.get('name'):
                    allowed_pool_url_map[p.get('name').lower()] = url
                yield_context += f"- [{p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')})]({url}): APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
            else:
                yield_context += f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"

        # Compile active trades context
        if user_trades:
            trade_context = "User's Active Paper Trades:\n"
            for t in user_trades:
                p = t.get("protocols", {}) or {}
                # Find current APY from yields list
                current_apy = None
                if yields:
                    for y in yields:
                        if y.get("protocol_id") == t.get("protocol_id"):
                            current_apy = y.get("apy")
                            break
                
                # Fallback to entry APY if current APY is not in the recent yields snapshot
                if current_apy is None:
                    current_apy = t.get("entry_apy")
                
                apy_str = f"{current_apy:.2f}%" if current_apy is not None else "N/A"
                url = clean_pool_url(p.get("pool_address"))
                if url:
                    t_name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                    allowed_pool_url_map[t_name_key] = url
                    if p.get('name'):
                        allowed_pool_url_map[p.get('name').lower()] = url
                    trade_context += f"- Protocol: [{p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')})]({url}) | Entry APY: {t['entry_apy']:.2f}% | Current APY: {apy_str} | Current Investment: ${t['simulated_investment_usd']:.2f}\n"
                else:
                    trade_context += f"- Protocol: {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}) | Entry APY: {t['entry_apy']:.2f}% | Current APY: {apy_str} | Current Investment: ${t['simulated_investment_usd']:.2f}\n"
        else:
            trade_context = "User has NO active paper trades right now.\n"

        system_prompt = f"""You are YieldSage's premium, autonomous DeFi research and advisory agent.
Your goal is to construct a beautiful, engaging, data-dense, and professional hourly Telegram broadcast message for a user.

User Settings:
- Target Risk Profile: {risk_preference.upper()}

The message MUST contain ALL of the following distinct sections, clearly formatted with headers and emojis:
1. 📊 **Solana Yield Snapshots & Recommendations**: Highlight the top-performing yield pools matching their risk tier. Provide 2-3 specific pool names with current APYs, TVLs, and verify links. Consistently append "Reason: [AI Reasoning from context]" at the end of each bullet on the same line. IMPORTANT: Only use URLs that appear EXACTLY in the context below. If a pool has an address link in the context, copy it exactly into a Markdown link. If no address is in the context, write the name as plain text — never invent or construct a URL.
2. 💼 **Personalized Portfolio Analysis**:
   - You MUST analyze and list EVERY SINGLE trade in the User's Active Paper Trades context. Do not omit, group, or skip any of them. For EACH trade, output exactly one bullet point formatted as follows:
     • [Protocol Name (Pool Name)](exact_url_from_context_if_available): Entry X.XX% APY → Current Y.YY% APY [Status symbol/text] — [Detailed personalized analysis of this position, specifically checking for performance changes, yield sustainability, pool risk, TVL shifts, and whether it is underperforming by 2%+ or outperforming, with actionable advice].
     CRITICAL: Only use the URL that appears in the context. If no URL is in the context for this pool, write the name as plain text — no link.
     For status symbols/text:
     - If underperforming by 2%+: ⚠️ Underperforming by Z.ZZ%
     - If performing normally or close (within 2%): 🟢 Steady
     - If outperforming: ✅ Outperforming
   - If the user does not have active paper trades: Explain the benefits of simulating trades to track yields, and suggest a specific pool to simulate first.
3. 💡 **Actionable DeFi Intelligence**: Provide a short, senior-engineer level market insight specific to Solana DeFi (e.g. stablecoin yields, LST yields, transaction speeds, pool TVL inflows, etc.).

Strict Formatting Rules:
1. NO RAW UNDERSCORES: Never output bare underscores (like USDT_USDC). Always format cleanly (e.g. USDT-USDC) or escape them to avoid breaking Telegram's parser.
2. NO HEADERS: Do not use #, ##, or ###. Instead, bold your section titles like this: **Section Title**
3. NO TABLES: Do not use Markdown tables (e.g. | column | column |). Instead, use bullet points.
4. NO DIVIDERS: Do not use horizontal rules (---). Use blank lines to separate sections.
5. FORMATTING: Use double asterisks for bolding: **bold text**.
6. PORTFOLIO ANALYSIS COMPLETENESS: You MUST include every single active trade in the portfolio. Never summarize them into a single line or say "and others". Each trade gets its own bullet and its own dedicated paragraph of detailed analysis and reasons.
7. LENGTH: Keep it professional, data-dense, and direct. Approximately 200-400 words (more if the user has multiple active trades). Keep it concise but ensure absolute completeness and detail. No preamble. Only output the final text.
8. ZERO HALLUCINATION OF EXAMPLE DATA: The pools, APYs, TVLs, transaction hashes (tx), and reasoning shown in the examples are for structural reference only. Under NO circumstances should you output any details from the examples (such as Clearpool USDT at 17.50%, transaction hash 0x10ad97e9301add5f844128c5d12b5b4949d6b1ba543fc2c5e29dbc54577bd96f, etc.) unless they are explicitly present in the live database context provided to you. If a pool or trade is not in the user's active trades or the live yield snapshot, you must never mention it.
"""

        try:
            response = await anthropic.messages.create(
                model=self.sonnet_model,
                max_tokens=1500,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Yields:\n{yield_context}\n\nTrades:\n{trade_context}\n\nGenerate the hourly update message now:"}
                ],
                temperature=0.4
            )
            result = response.content[0].text.strip()
            # Strip hallucinated or unregistered pool links before markdown cleaning
            result = enforce_authentic_pool_links(result, allowed_pool_url_map)
            return clean_telegram_markdown(result)
        except Exception as e:
            logger.error(f"Error generating personalized hourly update: {e}")
            return "⚠️ Sorry, I had trouble generating your hourly market update. I will try again next hour!"
