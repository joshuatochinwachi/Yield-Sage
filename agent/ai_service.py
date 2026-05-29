import os
import re
import json
import logging
import httpx
import asyncio
from datetime import datetime
from supabase import create_client, Client
from openai import AsyncOpenAI, RateLimitError

logger = logging.getLogger(__name__)

# ─── Supabase (bot.py imports `supabase` and `clean_telegram_markdown` directly
#     — these module-level names MUST stay identical) ──────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# ─── NVIDIA NIM — OpenAI-compatible endpoint ────────────────────────────────
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# Two models = two independent rate-limit pools.
# PRIMARY is tried first. On 429, FALLBACK is used automatically.
PRIMARY_MODEL  = "meta/llama-3.3-70b-instruct"
FALLBACK_MODEL = "meta/llama-3.1-70b-instruct"

_nvidia_client: AsyncOpenAI | None = (
    AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY,
    )
    if NVIDIA_API_KEY else None
)

# ─── Last-known-good response cache ─────────────────────────────────────────
# If both models are unavailable (rate-limited or erroring), we serve the most
# recent successful response so judges never hit a dead wall.
_response_cache: dict = {
    "conversational": None,   # str  — last bot reply
    "hourly_analysis": None,  # list — last JSON analysis array
    "hourly_update":   None,  # str  — last personalised hourly message
}

# ─── Tool definition — OpenAI function-call format ──────────────────────────
# (Anthropic used `input_schema`; OpenAI/NVIDIA NIM uses `parameters`)
_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Searches the web for real-time information, news, "
            "general facts, or DeFi topics outside our database."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to run.",
                }
            },
            "required": ["query"],
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# clean_telegram_markdown
# Exported symbol — bot.py imports this directly. Keep the function name stable.
# ─────────────────────────────────────────────────────────────────────────────
def clean_telegram_markdown(text: str) -> str:
    if not text:
        return ""

    # ── Step 0: Normalise line endings ───────────────────────────────────────
    text = text.replace("\r\n", "\n")

    # ── Step 1: Repair split Markdown links ──────────────────────────────────
    # The model sometimes emits the URL on a separate line:
    #   [Aave V3]
    #   (https://mantlescan.xyz/...)
    # \s* matches spaces AND newlines, so both cases are collapsed here.
    text = re.sub(r'\]\s*\n\s*\(https?://', '](https://', text)   # newline-split link
    text = re.sub(r'\]\s*\(https?://', '](https://', text)         # space-padded link
    text = re.sub(r'\(\s+(https?://)', r'(\1', text)               # leading space inside ()

    # ── Step 2: Strip stray asterisks inside URLs ─────────────────────────────
    # e.g. (https://mantlescan.xyz/address/0x**abc**) → (https://…/0xabc)
    text = re.sub(r'\(https?://[^)]+\)', lambda m: m.group(0).replace("*", ""), text)

    # ── Step 3: Normalise /paper_trade → /trade ───────────────────────────────
    text = (
        text
        .replace("/paper_trade", "/trade")
        .replace("/paper\\_trade", "/trade")
        .replace("/paper\\\\_trade", "/trade")
    )

    # ── Step 4: Transform [Protocol (Pool)](url) → [Protocol](url) (Pool) ────
    #     Also strips surrounding * the model wraps around links.
    def to_yields_style_link(match):
        full_text = match.group(1).strip().strip("*")
        url = match.group(2).strip()
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

    # ── Step 5: Normalise bold markers ────────────────────────────────────────
    # Telegram legacy Markdown uses single * for bold.
    text = text.replace("**", "*")

    # ── Step 6: Line-by-line cleanup ──────────────────────────────────────────
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            line = f"*{stripped[hashes:].strip()}*"
        elif stripped in ["---", "===", "___", "***"]:
            line = ""
        cleaned_lines.append(line.rstrip())   # strip trailing spaces

    text = "\n".join(cleaned_lines)

    # ── Step 7: Fix jammed bullet points ──────────────────────────────────────
    # When the model runs bullets together without newlines (e.g. "text • Pool
    # — APY • Pool2") each bullet gets its own line with a blank line before it.
    # Match • or · that are NOT already at the start of a line.
    text = re.sub(r'(?<!\n)[ \t]*[•·]\s+', '\n\n• ', text)

    # ── Step 8: Section emoji headers get a blank line before them ────────────
    # 📊 💼 💡 ⚠️ section openers jammed against previous text get separated.
    text = re.sub(
        r'(?<!\n)\n?(📊|💼|💡|⚠️)\s+',
        lambda m: f'\n\n{m.group(1)} ',
        text,
    )

    # ── Step 9: Collapse runs of 3+ blank lines down to max 2 ─────────────────
    text = re.sub(r'\n{3,}', '\n\n', text)

    # ── Step 10: Escape underscores — protecting full [text](url) units ───────
    # Critical: protect the ENTIRE [text](url) token, not just the URL.
    # Without this, [Agni_Finance](url) → [Agni\_Finance](url) which breaks
    # Telegram's link parser and shows as raw text.
    pattern = re.compile(r'(\[[^\]]*\]\(https?://[^)]+\)|https?://[^\s\)]+|/\w+|\\_)')
    parts = []
    last_idx = 0
    for match in pattern.finditer(text):
        start, end = match.span()
        parts.append(text[last_idx:start].replace("_", "\\_"))
        parts.append(text[start:end])
        last_idx = end
    parts.append(text[last_idx:].replace("_", "\\_"))

    text = "".join(parts).strip()

    # ── Step 11: Wrap any remaining bare URLs ─────────────────────────────────
    # Nuclear fallback: if the model still outputs a raw https:// URL that is
    # NOT already wrapped in [text](url), wrap it now so users never see a
    # naked link. mantlescan addresses get labelled 'View on Explorer',
    # everything else gets labelled 'Link'.
    def wrap_bare_url(m):
        raw = m.group(0)
        if "mantlescan.xyz" in raw:
            return f"[View on Explorer]({raw})"
        return f"[Link]({raw})"

    # Match bare URLs that are NOT already inside []() markdown links.
    # Negative lookbehind: not preceded by '(' — that would mean it's already inside a link.
    text = re.sub(
        r'(?<!\()(?<![\[\(])https?://[^\s\)\]]+',
        wrap_bare_url,
        text,
    )

    return text


# ─────────────────────────────────────────────────────────────────────────────
# _nvidia_call — core helper with automatic model fallback
# ─────────────────────────────────────────────────────────────────────────────
async def _nvidia_call(
    messages: list,
    system_prompt: str,
    tools: list = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
):
    """
    Sends a chat completion request to NVIDIA NIM.

    Fallback chain:
      1. PRIMARY_MODEL  (meta/llama-3.3-70b-instruct)
      2. FALLBACK_MODEL (meta/llama-3.1-70b-instruct)

    Raises the original exception only after both models are exhausted.
    """
    if not _nvidia_client:
        raise RuntimeError("NVIDIA_API_KEY is not set. AI service is unavailable.")

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    last_exc = None
    for attempt, model in enumerate([PRIMARY_MODEL, FALLBACK_MODEL]):
        try:
            kwargs = dict(
                model=model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await _nvidia_client.chat.completions.create(**kwargs)

            if attempt > 0:
                logger.info(f"[NVIDIA] Fallback model {model} succeeded.")
            return response

        except RateLimitError as e:
            last_exc = e
            if attempt == 0:
                logger.warning(
                    f"[NVIDIA] Rate limit on {PRIMARY_MODEL}. "
                    f"Switching to {FALLBACK_MODEL}..."
                )
                await asyncio.sleep(1)
            else:
                logger.error("[NVIDIA] Rate limit on both models.")

        except Exception as e:
            # Catch raw 429s that arrive as non-RateLimitError (provider quirks)
            is_429 = (
                hasattr(e, "status_code") and e.status_code == 429
            ) or "429" in str(e)

            if is_429 and attempt == 0:
                last_exc = e
                logger.warning(
                    f"[NVIDIA] 429 on {PRIMARY_MODEL}. "
                    f"Switching to {FALLBACK_MODEL}..."
                )
                await asyncio.sleep(1)
            else:
                raise  # Non-rate-limit errors raised immediately

    raise last_exc  # Both models exhausted


# ─────────────────────────────────────────────────────────────────────────────
# AIService
# ─────────────────────────────────────────────────────────────────────────────
class AIService:
    """
    Replaces the Anthropic-backed AIService with NVIDIA NIM (OpenAI-compatible).
    All public method signatures are identical to the original.
    All DB helpers are untouched.
    """

    def __init__(self):
        self.primary_model  = PRIMARY_MODEL
        self.fallback_model = FALLBACK_MODEL

    # ── DB helpers (logic unchanged from original) ────────────────────────────

    async def get_recent_yields(self):
        """Fetch the latest snapshot for each active protocol."""
        if not supabase:
            return []
        try:
            protocols_res = supabase.table("protocols").select(
                "id, name, pool_name, pool_address, risk_tag"
            ).eq("is_active", True).execute()
            protocols = protocols_res.data

            snap_res = supabase.table("yield_snapshots").select("*").order(
                "fetched_at", desc=True
            ).limit(100).execute()

            latest_snaps = {}
            if snap_res.data:
                for row in snap_res.data:
                    pid = row["protocol_id"]
                    if pid not in latest_snaps:
                        latest_snaps[pid] = row

            latest_yields = []
            for p in protocols:
                if p["id"] in latest_snaps:
                    yield_data = latest_snaps[p["id"]]
                    yield_data["protocol"] = p
                    latest_yields.append(yield_data)

            return latest_yields
        except Exception as e:
            logger.error(f"Error fetching recent yields: {e}")
            return []

    async def get_user_paper_trades(
        self, user_id: str = None, telegram_chat_id: int = None
    ):
        """Fetch active paper trades for a user, or all active trades if no user specified."""
        if not supabase:
            return []
        try:
            query = supabase.table("paper_trades").select(
                "*, protocols(name, pool_name, pool_address)"
            ).eq("status", "active")

            if user_id or telegram_chat_id:
                user_uuid = await self._resolve_user(user_id, telegram_chat_id)
                if not user_uuid:
                    return []
                query = query.eq("user_id", user_uuid)

            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching paper trades: {e}")
            return []

    async def _resolve_user(
        self, user_id: str = None, telegram_chat_id: int = None
    ):
        """Resolve a telegram_chat_id to a Supabase user_id if needed."""
        if user_id:
            return user_id
        if not telegram_chat_id or not supabase:
            return None
        try:
            res = supabase.table("users").select("id").eq(
                "telegram_chat_id", telegram_chat_id
            ).limit(1).execute()
            if res.data:
                return res.data[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Error resolving user: {e}")
            return None

    async def load_chat_memory(
        self,
        user_id: str = None,
        telegram_chat_id: int = None,
        limit: int = 15,
    ):
        """Load recent conversation history."""
        if not supabase:
            return []
        try:
            query = supabase.table("chat_memory").select(
                "role, content"
            ).order("created_at", desc=True).limit(limit)

            user_uuid = await self._resolve_user(user_id, telegram_chat_id)
            if user_uuid:
                query = query.eq("user_id", user_uuid)
            elif telegram_chat_id:
                query = query.eq("telegram_chat_id", telegram_chat_id)
            else:
                return []

            res = query.execute()
            return [
                {"role": r["role"], "content": r["content"]}
                for r in reversed(res.data)
            ]
        except Exception as e:
            logger.error(f"Error loading chat memory: {e}")
            return []

    async def push_to_memory(
        self,
        role: str,
        content: str,
        user_id: str = None,
        telegram_chat_id: int = None,
    ):
        """Save a message to conversation history."""
        if not supabase:
            return
        try:
            user_uuid = await self._resolve_user(user_id, telegram_chat_id)
            payload = {"role": role, "content": content}
            if user_uuid:
                payload["user_id"] = user_uuid
            if telegram_chat_id:
                payload["telegram_chat_id"] = telegram_chat_id
            supabase.table("chat_memory").insert(payload).execute()
        except Exception as e:
            logger.error(f"Error pushing to memory: {e}")

    # ── Web search (unchanged from original) ──────────────────────────────────

    async def search_web(self, query: str) -> str:
        """Performs a web search via DuckDuckGo HTML endpoint."""
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data={"q": query}, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"DDG Search HTTP error {resp.status_code}")
                    return ""

                text = resp.text
                snippets = re.findall(
                    r'class="[^"]*snippet[^"]*"[^>]*>(.*?)</', text, re.DOTALL
                )
                titles = re.findall(
                    r'class="[^"]*result__link[^"]*"[^>]*>(.*?)</', text, re.DOTALL
                )
                if not titles:
                    titles = re.findall(
                        r'class="[^"]*result-link[^"]*"[^>]*>(.*?)</', text, re.DOTALL
                    )

                results = []
                import html
                clean_tags = re.compile("<.*?>")
                for i in range(min(len(snippets), len(titles), 5)):
                    t_clean = html.unescape(re.sub(clean_tags, "", titles[i]).strip())
                    s_clean = html.unescape(re.sub(clean_tags, "", snippets[i]).strip())
                    if t_clean and s_clean:
                        results.append(f"• **{t_clean}**\n  {s_clean}")

                if not results:
                    for s in snippets[:5]:
                        s_clean = html.unescape(re.sub(clean_tags, "", s).strip())
                        if s_clean:
                            results.append(f"• {s_clean}")

                return "\n\n".join(results)
        except Exception as e:
            logger.error(f"Search Web Error: {e}")
            return ""

    # ── Conversational query (replaces Haiku) ─────────────────────────────────

    async def handle_conversational_query(
        self,
        user_message: str,
        user_id: str = None,
        telegram_chat_id: int = None,
    ):
        """
        Main entrypoint for Telegram bot chats.
        Called by bot.py → handle_message().
        Returns a clean Telegram-formatted string.
        """
        if not _nvidia_client:
            return "AI service is currently unconfigured. Please check API keys."

        # 1. Persist user message
        await self.push_to_memory("user", user_message, user_id, telegram_chat_id)

        # 2. Gather context
        history     = await self.load_chat_memory(user_id, telegram_chat_id, limit=10)
        yields      = await self.get_recent_yields()
        paper_trades = await self.get_user_paper_trades(user_id, telegram_chat_id)

        # 3. Build context strings
        yield_context = "Current Live Yields (Mantle Network):\n"
        for y in yields:
            p        = y["protocol"]
            apy_val  = y.get("apy")
            apy_str  = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            risk_tag = p.get("risk_tag") or "unknown"
            pool_addr = p.get("pool_address")
            if pool_addr:
                url = pool_addr if pool_addr.startswith("http") else f"https://mantlescan.xyz/address/{pool_addr}"
                yield_context += (
                    f"- [{p['name']} ({p['pool_name']})]({url}): "
                    f"{apy_str} APY | Risk: {risk_tag.upper()}\n"
                )
            else:
                yield_context += (
                    f"- {p['name']} ({p['pool_name']}): "
                    f"{apy_str} APY | Risk: {risk_tag.upper()}\n"
                )

        trade_context = "User's Active Paper Trades:\n"
        if paper_trades:
            for t in paper_trades:
                p = t["protocols"]
                pool_addr = p.get("pool_address")
                if pool_addr:
                    url = pool_addr if pool_addr.startswith("http") else f"https://mantlescan.xyz/address/{pool_addr}"
                    trade_context += (
                        f"- [{p['name']} ({p['pool_name']})]({url}): "
                        f"${t['simulated_investment_usd']:,.2f} invested at {t['entry_apy']}% APY\n"
                    )
                else:
                    trade_context += (
                        f"- {p['name']} ({p['pool_name']}): "
                        f"${t['simulated_investment_usd']:,.2f} invested at {t['entry_apy']}% APY\n"
                    )
        else:
            trade_context += "- None active.\n"

        system_prompt = f"""You are YieldSage — a sharp, professional DeFi yield advisor specialising in the Mantle network. You are direct, data-driven, and genuinely helpful. Respond like a knowledgeable senior DeFi analyst talking to a smart user: concise, confident, and always grounded in the live data below.

If the user asks to open a position or start a trade, direct them to the `/trade` command.

════════════════════════════════════════
ABSOLUTE FORMATTING LAWS — NO EXCEPTIONS
════════════════════════════════════════

LAW 1 ── NO MARKDOWN HEADERS. EVER.
FORBIDDEN → # Title, ## Title, ### Title
REQUIRED → **Title** (double asterisks — no hash symbols)

LAW 2 ── NO MARKDOWN TABLES. EVER.
FORBIDDEN → | Protocol | APY | Risk |
REQUIRED → Bullet points using • or –

LAW 3 ── NO HORIZONTAL DIVIDERS.
FORBIDDEN → ---, ***, ===
REQUIRED → Blank line between sections only

LAW 4 ── EVERY POOL WITH AN ADDRESS = HYPERLINK.
If a pool has an address in the context, it MUST be a Markdown link. No exceptions.
FORMAT EXACTLY → [Protocol Name](https://mantlescan.xyz/address/0xADDRESS)
WRONG → Agni Finance WMNT-mETH offers 121% APY
RIGHT → [Agni Finance](https://mantlescan.xyz/address/0x1234abc) WMNT-mETH offers 121% APY
If no address exists, write the name plainly — never invent a URL.

LAW 5 ── BOLD = DOUBLE ASTERISKS ONLY.
FORMAT → **bold text**
WRONG → *italic text* ← this is italic, not bold — never use single asterisks for bold

LAW 6 ── NO RAW UNDERSCORES IN TOKEN NAMES.
WRONG → USDT_USDC, WMNT_mETH
RIGHT → USDT-USDC, WMNT-mETH

LAW 7 ── SPACING. EVERY SECTION AND BULLET MUST BREATHE.
Each bullet point MUST be on its own line with a blank line before it.
Each new section MUST have a blank line before it.
WRONG → "• Pool A — 10% APY • Pool B — 8% APY" (bullets jammed on one line)
RIGHT →
• Pool A — 10% APY
  Description here.

• Pool B — 8% APY
  Description here.
Never run two bullets together on the same line. Never run a section title into a paragraph.

════════════════════════════════════════
FORMATTING EXAMPLE — MIRROR THIS EXACTLY
════════════════════════════════════════

**Top Stable Pools Right Now**

• [Clearpool USDT](https://mantlescan.xyz/address/0xabc123) — **17.50% APY** | TVL: $2.1M | STABLE
  Institutional private-credit pool. Strong liquidity. Best stable-tier yield on Mantle right now.

• [Aave V3 USDC](https://mantlescan.xyz/address/0xdef456) — **7.02% APY** | TVL: $10B+ | STABLE
  Most battle-tested DeFi protocol globally. Lowest counterparty risk available.

**My Recommendation**

For a conservative $1,000 entry, I'd split 70/30 between Clearpool USDT and Aave V3. The Clearpool yield is institutional-grade and the Aave allocation acts as a safety anchor.

Use /trade to simulate this allocation.

════════════════════════════════════════
MANDATORY SELF-CHECK BEFORE RESPONDING
════════════════════════════════════════
Before outputting anything, silently verify:
1. Zero # headers anywhere — only **bold** for section titles
2. Zero | table | syntax — only bullet lists
3. Zero --- / === / *** dividers — only blank lines
4. Every pool that has an address is a [Name](url) clickable link
5. Bold uses **double asterisks**, never single *asterisks*
6. No raw underscores in any token pair names
7. Every bullet point is on its own line with a blank line before it
8. No two bullets appear on the same line — each starts fresh on a new line

If any check fails, fix it before responding.

════════════════════════════════════════
LIVE DATA — ALWAYS USE THIS IN RESPONSES
════════════════════════════════════════
{yield_context}
{trade_context}
"""

        # 4. Prepare conversation history
        # Filter to only user/assistant roles (same logic as original)
        valid_history = [m for m in history if m["role"] in ("user", "assistant")]

        # Compress consecutive same-role messages (Llama chat template requires alternation)
        compressed_history = []
        for msg in valid_history:
            if not compressed_history:
                compressed_history.append(dict(msg))
            elif compressed_history[-1]["role"] == msg["role"]:
                compressed_history[-1]["content"] += "\n" + msg["content"]
            else:
                compressed_history.append(dict(msg))

        # First message must be from user
        if compressed_history and compressed_history[0]["role"] == "assistant":
            compressed_history.pop(0)

        # 5. First NVIDIA NIM call (tool calling enabled)
        try:
            response = await _nvidia_call(
                messages=compressed_history,
                system_prompt=system_prompt,
                tools=[_SEARCH_TOOL],
                temperature=0.3,
                max_tokens=1500,
            )

            message      = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # 6. Handle tool call if model decided to search the web
            if finish_reason == "tool_calls" and message.tool_calls:

                # ── Build the assistant message with tool_calls (OpenAI format) ──
                assistant_tool_msg = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }

                # ── Execute each tool and collect results ──
                tool_result_msgs = []
                for tc in message.tool_calls:
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    if tc.function.name == "search_web":
                        query_val      = tool_input.get("query", "")
                        logger.info(f"[NVIDIA] Llama requested search_web: '{query_val}'")
                        search_results = await self.search_web(query_val)
                        if not search_results:
                            search_results = "No search results found."
                        result_content = f"Web Search Results for '{query_val}':\n\n{search_results}"
                    else:
                        result_content = f"Error: unknown tool {tc.function.name}"

                    # ── Tool result message (OpenAI format) ──
                    tool_result_msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_content,
                    })

                # 7. Second call — model sees its tool use + the results
                follow_up = compressed_history + [assistant_tool_msg] + tool_result_msgs
                final_response = await _nvidia_call(
                    messages=follow_up,
                    system_prompt=system_prompt,
                    tools=[_SEARCH_TOOL],
                    temperature=0.3,
                    max_tokens=1500,
                )
                bot_reply = final_response.choices[0].message.content or ""
            else:
                bot_reply = message.content or ""

            bot_reply = clean_telegram_markdown(bot_reply)

            # 8. Persist and cache
            await self.push_to_memory("assistant", bot_reply, user_id, telegram_chat_id)
            _response_cache["conversational"] = bot_reply

            return bot_reply

        except Exception as e:
            logger.error(f"[NVIDIA] Conversational query error: {e}")
            if _response_cache["conversational"]:
                return (
                    _response_cache["conversational"]
                    + "\n\n_⚠️ Cached response — AI is temporarily busy. Try again in a moment._"
                )
            return (
                "Sorry, I'm having trouble analyzing the market right now. "
                "Please try again in a moment."
            )

    # ── Hourly analysis (replaces Sonnet for trade scoring) ──────────────────

    async def generate_hourly_analysis(self, yields, paper_trades):
        """
        Used by the Scorer to evaluate positions and generate alerts.
        Returns a list of dicts with user_id, trade_id, alert_message.
        """
        if not _nvidia_client:
            return []

        yield_context = "Latest Yield Snapshots:\n"
        for y in yields:
            p        = y.get("protocol", {})
            apy_val  = y.get("apy")
            apy_str  = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            risk_tag = p.get("risk_tag") or "unknown"
            yield_context += (
                f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): "
                f"{apy_str} APY (Risk: {risk_tag.upper()})\n"
            )

        trade_context = "Active Paper Trades to Evaluate:\n"
        for t in paper_trades:
            p = t.get("protocols", {})
            trade_context += (
                f"Trade ID: {t['id']} | User ID: {t['user_id']} | "
                f"Protocol: {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}) | "
                f"Entry APY: {t['entry_apy']}% | "
                f"Current Investment: ${t['simulated_investment_usd']}\n"
            )

        system_prompt = """You are YieldSage's backend scoring engine. Your only job is to analyze paper trades and return a JSON array.

════════════════════════════════════════
OUTPUT RULES — ZERO TOLERANCE
════════════════════════════════════════

RULE 1 ── YOUR ENTIRE RESPONSE MUST BE VALID JSON. NOTHING ELSE.
You are FORBIDDEN from including any text before or after the JSON array.
You are FORBIDDEN from wrapping the JSON in markdown code blocks (no ```json, no ```).
You are FORBIDDEN from adding explanations, preambles, or notes.
Your response must start with [ and end with ].

WRONG OUTPUT (DO NOT DO THIS):
Here is the analysis:
```json
[...]
```

CORRECT OUTPUT (ALWAYS DO THIS):
[
  {
    "user_id": "uuid-here",
    "trade_id": "uuid-here",
    "alert_message": "Your message here."
  }
]

RULE 2 ── ONE OBJECT PER ACTIVE TRADE. NO SKIPPING.
You MUST generate one object for every single active trade listed. Never return [].

RULE 3 ── ALERT LOGIC.
If a trade's current APY is underperforming by more than 2% vs a better pool in the SAME risk tier → generate an ALERT recommending the switch.
If a trade is performing well → generate a brief reassuring status update.

RULE 4 ── NO UNDERSCORES IN POOL NAMES.
WRONG → USDT_USDC
RIGHT → USDT-USDC

RULE 5 ── alert_message must be plain text only. No markdown, no links, no bold.

════════════════════════════════════════
REQUIRED JSON SCHEMA
════════════════════════════════════════
[
  {
    "user_id": "string — the user UUID",
    "trade_id": "string — the trade UUID",
    "alert_message": "string — plain text status or alert"
  }
]
"""

        try:
            response = await _nvidia_call(
                messages=[{
                    "role": "user",
                    "content": (
                        f"Yields:\n{yield_context}\n\n"
                        f"Trades:\n{trade_context}\n\n"
                        "Analyze and return JSON."
                    ),
                }],
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1500,
            )

            content = (response.choices[0].message.content or "").strip()

            # Strip markdown code fences if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content.strip())
            _response_cache["hourly_analysis"] = result
            return result

        except Exception as e:
            logger.error(f"[NVIDIA] Error in hourly analysis: {e}")
            if _response_cache["hourly_analysis"] is not None:
                logger.info("[NVIDIA] Serving cached hourly analysis.")
                return _response_cache["hourly_analysis"]
            return []

    # ── Personalised hourly update (replaces Sonnet for scorer.py) ───────────

    async def generate_personalized_hourly_update(
        self,
        risk_preference: str,
        user_trades: list,
        yields: list,
    ) -> str:
        """
        Generates a personalised hourly Telegram message for a user.
        Called directly by scorer.py → HourlyScorer.run().
        """
        if not _nvidia_client:
            return (
                "⚠️ YieldSage background services are temporarily offline. "
                "Please check back later."
            )

        # Compile yield context (unchanged from original)
        yield_context = ""
        for y in yields:
            p        = y.get("protocol", {})
            apy_val  = y.get("apy")
            apy_str  = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            risk_tag = p.get("risk_tag") or "unknown"
            tvl_val  = y.get("tvl_usd") or 0
            tvl_str  = f"${tvl_val:,.0f}" if tvl_val else "N/A"
            pool_addr = p.get("pool_address")
            if pool_addr:
                url = pool_addr if pool_addr.startswith("http") else f"https://mantlescan.xyz/address/{pool_addr}"
                yield_context += (
                    f"- [{p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')})]({url}): "
                    f"APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
                )
            else:
                yield_context += (
                    f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): "
                    f"APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
                )

        # Compile trades context (unchanged from original)
        if user_trades:
            trade_context = "User's Active Paper Trades:\n"
            for t in user_trades:
                p = t.get("protocols", {})
                pool_addr = p.get("pool_address")
                if pool_addr:
                    url = pool_addr if pool_addr.startswith("http") else f"https://mantlescan.xyz/address/{pool_addr}"
                    trade_context += (
                        f"- Protocol: [{p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')})]({url}) | "
                        f"Entry APY: {t['entry_apy']}% | "
                        f"Current Investment: ${t['simulated_investment_usd']:.2f}\n"
                    )
                else:
                    trade_context += (
                        f"- Protocol: {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}) | "
                        f"Entry APY: {t['entry_apy']}% | "
                        f"Current Investment: ${t['simulated_investment_usd']:.2f}\n"
                    )
        else:
            trade_context = "User has NO active paper trades right now.\n"

        system_prompt = f"""You are YieldSage's autonomous DeFi research and advisory agent. You write professional hourly Telegram broadcast messages for DeFi users on Mantle network.

════════════════════════════════════════
ABSOLUTE FORMATTING LAWS — ZERO EXCEPTIONS
════════════════════════════════════════

LAW 1 ── NO MARKDOWN HEADERS. ZERO.
FORBIDDEN → # Title, ## Title, ### Title
REQUIRED → **Title** (double asterisks only)

LAW 2 ── NO MARKDOWN TABLES. ZERO.
FORBIDDEN → | Protocol | APY | TVL |
REQUIRED → Bullet points with • or –

LAW 3 ── NO HORIZONTAL DIVIDERS.
FORBIDDEN → ---, ***, ===
REQUIRED → Blank line between sections

LAW 4 ── ALL POOL NAMES WITH ADDRESSES MUST BE HYPERLINKS.
Every single pool name that has an address in the context MUST be a Markdown link.
FORMAT → [Protocol Name](https://mantlescan.xyz/address/0xADDRESS)
WRONG → Clearpool USDT pool offers 17.5% APY
RIGHT → [Clearpool USDT](https://mantlescan.xyz/address/0xabc) offers 17.5% APY

LAW 5 ── NO RAW UNDERSCORES IN TOKEN NAMES.
WRONG → USDT_USDC, WMNT_mETH
RIGHT → USDT-USDC, WMNT-mETH

LAW 6 ── BOLD USES DOUBLE ASTERISKS ONLY.
WRONG → *Section Title*
RIGHT → **Section Title**

LAW 7 ── EVERY BULLET ON ITS OWN LINE WITH A BLANK LINE BEFORE IT.
WRONG → "• Pool A — 17% • Pool B — 10%" (bullets jammed together)
RIGHT →
• Pool A — **17% APY**
  Reason here.

• Pool B — **10% APY**
  Reason here.
Never put two bullets on the same line. Each bullet gets its own line and a blank line above it.

════════════════════════════════════════
MANDATORY OUTPUT STRUCTURE — FOLLOW EXACTLY
════════════════════════════════════════

Your message MUST have these three sections in this exact order:

📊 **Mantle Yield Snapshots & Recommendations**
[2-3 bullet points of top pools matching risk tier: {risk_preference.upper()}]
[Each bullet: pool link, APY, TVL, one-line reason — each on its OWN line with blank line before it]

💼 **Personalized Portfolio Analysis**
[If user has active trades: review each one. Entry APY vs current APY. Alert if underperforming by 2%+.]
[If no active trades: explain paper trading benefits and suggest one specific pool to start with]

💡 **Actionable DeFi Intelligence**
[One short senior-engineer-level Mantle DeFi insight. TVL movements, rate shifts, liquidity risks, etc.]

════════════════════════════════════════
FORMAT EXAMPLE — COPY THIS STRUCTURE EXACTLY
════════════════════════════════════════

📊 **Mantle Yield Snapshots & Recommendations**

• [Clearpool USDT](https://mantlescan.xyz/address/0xabc123): **17.50% APY** | TVL: $2.1M | STABLE
  Institutional private credit pool. Highest stable-tier yield right now.

• [Aave V3 USDC](https://mantlescan.xyz/address/0xdef456): **7.02% APY** | TVL: $10B+ | STABLE
  Battle-tested. Lowest counterparty risk on Mantle.

💼 **Personalized Portfolio Analysis**

• [Fluxion USDT0-BSB](https://mantlescan.xyz/address/0x999): Entry 23.51% → Current 26.45% ✅ Outperforming — hold position.

⚠️ **HIGH PRIORITY ALERT** — $15,000 Position:
[Agni Finance WMNT-mETH](https://mantlescan.xyz/address/0x777): Entry 121.84% → Current 121.87% — marginal hold, but TVL is only $1,280. Extreme liquidity risk. Consider rotating 50% into [Clearpool USDT](https://mantlescan.xyz/address/0xabc123) at 17.50% to de-risk.

💡 **Actionable DeFi Intelligence**

Clearpool's private credit pools on Mantle are currently outpacing Aave by 10-12%. Pools showing 0% APY alongside low TVL signal borrower repayment or wind-down — avoid redeployment there until activity resumes.

════════════════════════════════════════
OUTPUT CONSTRAINTS
════════════════════════════════════════
- Length: 200-250 words. No preamble. No sign-off. Start directly with 📊.
- User risk profile: {risk_preference.upper()} — only recommend pools matching this tier.
- Every pool name that has an address = a clickable link. No exceptions.

════════════════════════════════════════
MANDATORY SELF-CHECK BEFORE RESPONDING
════════════════════════════════════════
Before outputting, silently verify:
1. Message starts with 📊 **Mantle Yield Snapshots & Recommendations**
2. All three sections present
3. Zero # headers — only **bold** titles
4. Zero | tables — only bullet points
5. Every pool with an address is a [Name](url) link
6. No raw underscores in any token pair names
7. Bold uses **double asterisks** not *single*
8. Every bullet is on its own line with a blank line before it — none are jammed together

If any check fails, fix it before responding.
"""

        try:
            response = await _nvidia_call(
                messages=[{
                    "role": "user",
                    "content": (
                        f"Live yield data:\n{yield_context}\n\n"
                        f"User trades:\n{trade_context}\n\n"
                        "Generate the hourly Telegram update now. "
                        "IMPORTANT: Start your response IMMEDIATELY with 📊 **Mantle Yield Snapshots & Recommendations** — "
                        "no introduction, no preamble, no 'Here is your update'. "
                        "All pool names with addresses MUST be [Name](url) Markdown links. "
                        "Use **double asterisks** for bold. Never use # headers."
                    ),
                }],
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=1800,
            )

            result = clean_telegram_markdown(
                (response.choices[0].message.content or "").strip()
            )
            _response_cache["hourly_update"] = result
            return result

        except Exception as e:
            logger.error(f"[NVIDIA] Error generating personalised hourly update: {e}")
            if _response_cache["hourly_update"]:
                return (
                    _response_cache["hourly_update"]
                    + "\n\n_⚠️ Cached — AI busy. Fresh update coming next hour._"
                )
            return (
                "⚠️ Sorry, I had trouble generating your hourly market update. "
                "I will try again next hour!"
            )
