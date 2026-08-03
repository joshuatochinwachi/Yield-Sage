import os
import re
import json
import logging
import httpx
import asyncio
from datetime import datetime, timezone
from supabase import create_client, Client
from openai import AsyncOpenAI, RateLimitError

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

_PROVIDER_CONFIGS = [
    {
        "name":     "Cerebras",
        "env_key":  "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "primary":  "gpt-oss-120b",
        "fallback": "zai-glm-4.7",
    },
    {
        "name":     "Groq",
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "primary":  "openai/gpt-oss-120b",
        "fallback": "qwen/qwen3.6-27b",
    },
    {
        "name":     "NVIDIA",
        "env_key":  "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "primary":  "meta/llama-3.3-70b-instruct",
        "fallback": "meta/llama-3.1-70b-instruct",
    },
    {
        "name":     "Gemini",
        "env_key":  "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "primary":  "gemini-2.5-flash-lite",
        "fallback": "gemini-2.5-flash",
    },
]

def _init_providers() -> list:
    """
    Initialises only the providers whose API keys are present in env.
    Logs which providers are active so Railway logs make it obvious.
    """
    active = []
    for cfg in _PROVIDER_CONFIGS:
        key = os.getenv(cfg["env_key"])
        if key:
            client = AsyncOpenAI(base_url=cfg["base_url"], api_key=key)
            active.append({**cfg, "client": client})
            logger.info(f"[LLM] ✅ Provider ready: {cfg['name']} ({cfg['primary']})")
        else:
            logger.warning(f"[LLM] ⚠️  Provider skipped — no {cfg['env_key']} found: {cfg['name']}")
    if not active:
        logger.error("[LLM] ❌ No LLM providers configured. Check environment variables.")
    return active


_PROVIDERS: list = _init_providers()

# ─── Last-known-good response cache ─────────────────────────────────────────
# Served when ALL providers are unavailable so judges never see a dead wall.
_response_cache: dict = {
    "conversational": None,    # str  — last bot reply
    "hourly_analysis": None,   # list — last JSON analysis array
    "hourly_updates":  {},     # dict[user_id -> str] — per-user last message (NEVER share across users)
}

# ─── Tool definition — OpenAI function-call format ──────────────────────────
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
    Guarantees zero hallucinated, made-up, or mis-mapped pool links.
    If a pool in live data has no pool_address, any link created for it is stripped to plain text.
    If a pool has an authentic address, its link is preserved only if the URL matches its exact database record.
    """
    if not text:
        return text

    SYSTEM_PATTERNS = ["yieldsageai.xyz/verify", "yield.hollowscan.com/verify", "yieldsageai.xyz/dashboard", "yield.hollowscan.com/dashboard", "t.me/YieldSageBot"]

    def _validate_link(match):
        label = match.group(1).strip()
        url = match.group(2).strip()

        # Always allow system links
        if any(sys_pat in url for sys_pat in SYSTEM_PATTERNS):
            return f"[{label}]({url})"

        label_clean = re.sub(r'^[•\-\*\s]+', '', label).strip().lower()

        # Check direct or partial match against allowed pool url map
        matched_url = None
        for pool_key, valid_url in allowed_pool_url_map.items():
            if valid_url and (pool_key in label_clean or label_clean in pool_key):
                matched_url = valid_url
                break

        if matched_url and url.lower() == matched_url.lower():
            return f"[{label}]({url})"

        # Also allow if the exact URL is registered for any pool in allowed_pool_url_map
        all_valid_urls = {v.lower() for v in allowed_pool_url_map.values() if v}
        if url.lower() in all_valid_urls:
            return f"[{label}]({url})"

        # REJECT AND STRIP TO PLAIN TEXT
        logger.warning(f"[URL Guard] Stripped unverified/hallucinated link for '{label}': {url}")
        return label

    return re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', _validate_link, text)


# ─────────────────────────────────────────────────────────────────────────────
# clean_telegram_markdown
# Exported symbol — bot.py imports this directly. Keep the function name stable.
# ─────────────────────────────────────────────────────────────────────────────
def clean_telegram_markdown(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    # Repair split Markdown links
    text = re.sub(r'\]\s*\n\s*\(https?://', '](https://', text)
    text = re.sub(r'\]\s*\(https?://', '](https://', text)
    text = re.sub(r'\(\s+(https?://)', r'(\1', text)

    # Strip stray asterisks inside URLs
    text = re.sub(r'\(https?://[^)]+\)', lambda m: m.group(0).replace("*", ""), text)

    # Normalise /paper_trade → /trade
    text = (
        text
        .replace("/paper_trade", "/trade")
        .replace("/paper\\_trade", "/trade")
        .replace("/paper\\\\_trade", "/trade")
    )

    # Transform [Protocol (Pool)](url) → [Protocol](url) (Pool)
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

    # Normalise bold markers (Telegram legacy: single * = bold)
    text = text.replace("**", "*")

    # Line-by-line cleanup
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            line = f"*{stripped[hashes:].strip()}*"
        elif stripped in ["---", "===", "___", "***"]:
            line = ""
        cleaned_lines.append(line.rstrip())

    text = "\n".join(cleaned_lines)

    # Fix jammed bullet points
    text = re.sub(r'(?<!\n)[ \t]*[•·]\s+', '\n\n• ', text)

    # Section emoji headers get a blank line before them
    text = re.sub(
        r'(?<!\n)\n?(📊|💼|💡|⚠️)\s+',
        lambda m: f'\n\n{m.group(1)} ',
        text,
    )

    # Collapse runs of 3+ blank lines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Escape underscores — protect full [text](url) tokens
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

    # Wrap remaining bare URLs
    def wrap_bare_url(m):
        raw = m.group(0)
        if "solscan.io" in raw:
            return f"[View on Solscan]({raw})"
        return f"[Link]({raw})"

    text = re.sub(
        r'(?<!\()(?<![\[\(])https?://[^\s\)\]]+',
        wrap_bare_url,
        text,
    )

    return text


# ─────────────────────────────────────────────────────────────────────────────
# _llm_call — core helper with full three-provider cascade
# ─────────────────────────────────────────────────────────────────────────────
async def _llm_call(
    messages: list,
    system_prompt: str,
    tools: list = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    priority: str = "realtime",
):
    """
    Cascades through all configured providers until one succeeds.

    Attempt order (per provider):
      1. Primary model
      2. Fallback model
    Then moves to the next provider on any 429 or error.

    Full cascade sequence (both realtime and background):
      Cerebras/gpt-oss-120b → Cerebras/zai-glm-4.7 →
      SambaNova/Meta-Llama-3.3-70B → SambaNova/gemma-3-12b →
      Groq/openai/gpt-oss-120b → Groq/qwen/qwen3.6-27b →
      NVIDIA/llama-3.3-70b → NVIDIA/llama-3.1-70b →
      Gemini/gemini-2.5-flash-lite → Gemini/gemini-2.5-flash

    Background jobs use the same full cascade starting from Cerebras —
    fastest and most reliable. Falls through to NVIDIA/Gemini only if
    Cerebras/SambaNova/Groq are rate-limited or unavailable.

    Raises RuntimeError only after all slots are exhausted.
    """
    if not _PROVIDERS:
        raise RuntimeError("No LLM providers configured. Check API keys.")

    full_messages = [{"role": "system", "content": system_prompt}] + messages
    last_exc = None

    # Both realtime and background use the same full provider cascade.
    # Cerebras is always first — it is the fastest and most reliable.
    # NVIDIA is slower and prone to 504s; it is tried only after faster
    # providers (Cerebras, SambaNova, Groq) have been exhausted.
    provider_order = _PROVIDERS

    for provider in provider_order:
        for model in [provider["primary"], provider["fallback"]]:
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

                response = await provider["client"].chat.completions.create(**kwargs)
                logger.info(f"[LLM] ✅ Success — {provider['name']} / {model}")

                # Tool call response: content is legitimately None — valid, return immediately
                finish = response.choices[0].finish_reason
                content = response.choices[0].message.content
                tool_calls = response.choices[0].message.tool_calls

                if finish == "tool_calls" and tool_calls:
                    return response

                # Text response: empty content is a real failure — try next slot
                if not content or not content.strip():
                    logger.warning(f"[LLM] Empty response from {provider['name']} / {model} — trying next slot...")
                    last_exc = ValueError(f"Empty response from {model}")
                    await asyncio.sleep(0.3)
                    continue

                return response

            except RateLimitError as e:
                last_exc = e
                logger.warning(f"[LLM] 429 — {provider['name']} / {model}. Trying next slot...")
                await asyncio.sleep(0.5)

            except Exception as e:
                last_exc = e
                is_429 = (
                    hasattr(e, "status_code") and e.status_code == 429
                ) or "429" in str(e)
                level = "429 (raw)" if is_429 else "error"
                logger.warning(f"[LLM] {level} — {provider['name']} / {model}: {e}. Trying next slot...")
                await asyncio.sleep(0.3)

    logger.error("[LLM] ❌ All providers and models exhausted.")
    raise last_exc or RuntimeError("All LLM providers exhausted.")


# ─────────────────────────────────────────────────────────────────────────────
# Shared anti-hallucination prompt block
# Injected into every system prompt. Prevents the model from inventing
# numerical data (TVL, APY, addresses) not present in the live context.
# ─────────────────────────────────────────────────────────────────────────────
_DATA_INTEGRITY_BLOCK = """
════════════════════════════════════════
DATA INTEGRITY LAW — ZERO HALLUCINATION
════════════════════════════════════════

You are STRICTLY FORBIDDEN from inventing, estimating, or inferring ANY numerical data.
This applies to: APY values, TVL values, wallet addresses, protocol statistics, and any financial figures.

LAW ── ONLY USE NUMBERS EXPLICITLY PROVIDED IN THE LIVE DATA SECTION.
If a value is not listed in the context below: write "N/A" or omit the field entirely.
NEVER fill gaps with your training knowledge.

WRONG → "Aave V3 has $10B+ TVL" — unless that exact figure is in the context below.
WRONG → "The pool typically yields around 8%" — never estimate.
WRONG → [Kamino](https://solscan.io/account/SOMETHINGINVENTEDxyz) — invented address
RIGHT → Kamino — no link (address not in live data)
RIGHT → Only quote the exact TVL and APY values shown in the live data.

If the live data shows "TVL: N/A" — display "TVL: N/A". Do not replace it with an estimate.
If APY is missing for a pool — say "APY: data unavailable". Do not guess.
"""


# ─────────────────────────────────────────────────────────────────────────────
# AIService
# ─────────────────────────────────────────────────────────────────────────────
class AIService:
    """
    Multi-provider AI service.
    All public method signatures are identical to the original.
    All DB helpers are untouched.
    """

    def __init__(self):
        self.providers = _PROVIDERS

    # ── DB helpers ────────────────────────────────────────────────────────────

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

    # ── Web search ────────────────────────────────────────────────────────────

    async def search_web(self, query: str) -> str:
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

    # ── Conversational query ──────────────────────────────────────────────────

    async def handle_conversational_query(
        self,
        user_message: str,
        user_id: str = None,
        telegram_chat_id: int = None,
        thinking_callback=None,
    ):
        """
        Main entrypoint for Telegram bot chats.
        Called by bot.py → handle_message().
        Returns a clean Telegram-formatted string.
        """
        if not _PROVIDERS:
            return "AI service is currently unconfigured. Please check API keys."

        # 1. Persist user message
        await self.push_to_memory("user", user_message, user_id, telegram_chat_id)

        # 2. Gather context — DB reads run in parallel for speed
        history, yields, paper_trades = await asyncio.gather(
            self.load_chat_memory(user_id, telegram_chat_id, limit=10),
            self.get_recent_yields(),
            self.get_user_paper_trades(user_id, telegram_chat_id),
        )

        # 3. Build yield context — TVL included to prevent hallucination
        allowed_pool_url_map = {}
        yield_context = "Current Live Yields (Solana Network):\n"
        for y in yields:
            p         = y["protocol"]
            apy_val   = y.get("apy")
            tvl_val   = y.get("tvl_usd")
            apy_str   = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            tvl_str   = f"${tvl_val:,.0f}" if tvl_val else "N/A"
            risk_tag  = p.get("risk_tag") or "unknown"
            url       = clean_pool_url(p.get("pool_address"))
            if url:
                name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                allowed_pool_url_map[name_key] = url
                if p.get('name'):
                    allowed_pool_url_map[p.get('name').lower()] = url
                yield_context += (
                    f"- [{p['name']} ({p['pool_name']})]({url}): "
                    f"APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
                )
            else:
                yield_context += (
                    f"- {p['name']} ({p['pool_name']}): "
                    f"APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
                )

        # 4. Build trade context
        trade_context = "User's Active Paper Trades:\n"
        if paper_trades:
            for t in paper_trades:
                p = t["protocols"]
                url = clean_pool_url(p.get("pool_address"))
                if url:
                    name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                    allowed_pool_url_map[name_key] = url
                    if p.get('name'):
                        allowed_pool_url_map[p.get('name').lower()] = url
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

        system_prompt = f"""You are YieldSage — a sharp, professional DeFi yield advisor specialising in the Solana ecosystem. You are direct, data-driven, and genuinely helpful. Respond like a knowledgeable senior DeFi analyst talking to a smart user: concise, confident, and always grounded in the live data below.

If the user asks questions like "How can I simulate a trade?", "I want to paper trade", "Simulate a trade for me using $1000 (or any amount) in <any pool>", or similar, you MUST reply with these exact three options/formats:
1. Use the /trade command and simulate trade from the list of pools/yield opportunities. Follow the instructions from there.
2. Use this format that the bot uses: /trade id=<pool_id> address=<pool_address> amount=<amount> token=<protocol and token_or_pool_name>
   Example:
   /trade id=b1a2c3d4-e5f6-7890-abcd-1234567890ab address=ByYiZxp8QrdN9qbdtaAiePN8AAr3qvTPppNJDpf5DVJ5 amount=1000 token=kamino-finance (USDC)
   Note: Using the pool's unique ID guarantees 100% accurate simulation matching even if multiple pools share an address.
3. Simulate a trade directly from the preferred pool/yield opportunity on the web dashboard at [yieldsageai.xyz/dashboard](https://yieldsageai.xyz/dashboard).
{_DATA_INTEGRITY_BLOCK}
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
FORMAT EXACTLY → [Protocol Name](https://solscan.io/account/ADDRESS)
WRONG → Kamino USDC offers 8% APY
RIGHT → [Kamino](https://solscan.io/account/abc123) USDC offers 8% APY
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

LAW 8 ── NEVER INVENT BLOCKCHAIN EXPLORER LINKS.
You are FORBIDDEN from constructing a solscan.io URL unless the EXACT address is provided in the LIVE DATA section.
If a protocol or pool has no address in the live data, write its name plainly — no link.
WRONG → [Kamino](https://solscan.io/account/abc123) ← if abc123 is not in the live data
RIGHT → Kamino ← plain text when address is not in live data

LAW 9 ── INTELLIGENT SPLITTING FOR LONG MESSAGES.
If your response will be very long (e.g. listing many pools, or analyzing 4+ positions), you MUST intelligently split the response into separate message parts. Between each part, place the exact separator token: <<<PART_BREAK>>> on its own line. Rules for splitting:
- Each part must be independently readable, complete sentences, and perfectly formatted.
- Every Markdown link [text](url) must be fully closed within the same part — never split a link across parts.
- Every bold **text** must be opened and closed within the same part.
- Place the break at a natural boundary (end of a section or between bullet points).
- NEVER place the break mid-sentence, mid-link, or mid-bullet.

════════════════════════════════════════
FORMATTING EXAMPLE — MIRROR THIS EXACTLY
════════════════════════════════════════

**Top Stable Pools Right Now**

• [Kamino USDC](https://solscan.io/account/abc123) — **8.50% APY** | TVL: $2,100,000 | STABLE
  Institutional lending vault. Best stable-tier yield on Solana right now.

• [MarginFi SOL](https://solscan.io/account/def456) — **7.02% APY** | TVL: $3,682,789 | STABLE
  Most battle-tested Solana lending protocol. Lowest counterparty risk available.

**My Recommendation**

For a conservative $1,000 entry, I'd split 70/30 between Kamino USDC and MarginFi USDC. Kamino carries higher yield, MarginFi anchors your downside.

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
9. ALL numerical values (APY, TVL) copied exactly from LIVE DATA — never invented
10. If no address exists for a pool, write the name plainly — never invent a URL.

If any check fails, fix it before responding.

════════════════════════════════════════
LIVE DATA — USE ONLY THESE VALUES
════════════════════════════════════════
{yield_context}
{trade_context}
"""

        # 5. Prepare conversation history
        valid_history = [m for m in history if m["role"] in ("user", "assistant")]
        compressed_history = []
        for msg in valid_history:
            if not compressed_history:
                compressed_history.append(dict(msg))
            elif compressed_history[-1]["role"] == msg["role"]:
                compressed_history[-1]["content"] += "\n" + msg["content"]
            else:
                compressed_history.append(dict(msg))
        if compressed_history and compressed_history[0]["role"] == "assistant":
            compressed_history.pop(0)

        # 6. LLM call with tool use
        # If response takes more than 3 seconds, send a "thinking" message first.
        # If it responds faster, the timer is cancelled and nothing extra is sent.
        _thinking_sent = False

        async def _thinking_guard():
            nonlocal _thinking_sent
            await asyncio.sleep(3)
            if thinking_callback and not _thinking_sent:
                _thinking_sent = True
                try:
                    await thinking_callback()
                except Exception:
                    pass  # never let a notification failure break the main flow

        try:
            guard_task = asyncio.create_task(_thinking_guard())
            response = await _llm_call(
                messages=compressed_history,
                system_prompt=system_prompt,
                tools=[_SEARCH_TOOL],
                temperature=0.3,
                max_tokens=3500,
            )
            guard_task.cancel()  # response arrived — kill the thinking timer

            message       = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # Guard against empty response — LLMs occasionally returns 200 OK
            # with empty content. Force fallback rather than crashing.
            # if not message.content or not message.content.strip():
            #     logger.warning(f"[LLM] Empty response from {response.model} — retrying cascade")
            #     raise ValueError("Empty response content from LLM")

            # Handle tool call if model decided to search the web
            if finish_reason == "tool_calls" and message.tool_calls:

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

                tool_result_msgs = []
                for tc in message.tool_calls:
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    if tc.function.name == "search_web":
                        query_val      = tool_input.get("query", "")
                        logger.info(f"[LLM] Tool call — search_web: '{query_val}'")
                        search_results = await self.search_web(query_val)
                        if not search_results:
                            search_results = "No search results found."
                        result_content = f"Web Search Results for '{query_val}':\n\n{search_results}"
                    else:
                        result_content = f"Error: unknown tool {tc.function.name}"

                    tool_result_msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_content,
                    })

                follow_up = compressed_history + [assistant_tool_msg] + tool_result_msgs
                final_response = await _llm_call(
                    messages=follow_up,
                    system_prompt=system_prompt,
                    tools=[_SEARCH_TOOL],
                    temperature=0.3,
                    max_tokens=3500,
                )
                bot_reply = (final_response.choices[0].message.content or "").strip()
                if not bot_reply:
                    bot_reply = "⚠️ I didn't quite catch that — could you rephrase or try again?"
            else:
                bot_reply = (message.content or "").strip()
                if not bot_reply:
                    bot_reply = "⚠️ I didn't quite catch that — could you rephrase or try again?"

            # Strip any hallucinated or null-address pool links before returning.
            # allowed_pool_url_map was built earlier in this function from live DB data.
            # Do NOT call clean_telegram_markdown here — bot.py does exactly one clean pass
            # per chunk after splitting, preventing double-escaping of underscores in links.
            bot_reply = enforce_authentic_pool_links(bot_reply, allowed_pool_url_map)
            await self.push_to_memory("assistant", bot_reply, user_id, telegram_chat_id)
            _response_cache["conversational"] = bot_reply
            return bot_reply

        except Exception as e:
            logger.error(f"[LLM] All providers failed for conversational query: {e}")
            return "⚠️ I didn't quite catch that — could you rephrase or try again?"

    # ── Hourly analysis ───────────────────────────────────────────────────────

    async def generate_hourly_analysis(self, yields, paper_trades):
        """
        Used by the Scorer to evaluate positions and generate alerts.
        Returns a list of dicts with user_id, trade_id, alert_message.
        """
        if not _PROVIDERS:
            return []

        yield_context = "Latest Yield Snapshots:\n"
        for y in yields:
            p        = y.get("protocol", {})
            apy_val  = y.get("apy")
            tvl_val  = y.get("tvl_usd")
            apy_str  = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            tvl_str  = f"${tvl_val:,.0f}" if tvl_val else "N/A"
            risk_tag = p.get("risk_tag") or "unknown"
            yield_context += (
                f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): "
                f"APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
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

        system_prompt = f"""You are YieldSage's backend scoring engine. Your only job is to analyze paper trades and return a JSON array.
{_DATA_INTEGRITY_BLOCK}
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
  {{
    "user_id": "uuid-here",
    "trade_id": "uuid-here",
    "alert_message": "Your message here."
  }}
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

RULE 6 ── Use ONLY APY and TVL values from the yield snapshots above. Never invent numbers.

════════════════════════════════════════
REQUIRED JSON SCHEMA
════════════════════════════════════════
[
  {{
    "user_id": "string — the user UUID",
    "trade_id": "string — the trade UUID",
    "alert_message": "string — plain text status or alert"
  }}
]
"""

        try:
            response = await _llm_call(
                messages=[{
                    "role": "user",
                    "content": (
                        f"Yields:\n{yield_context}\n\n"
                        f"Trades:\n{trade_context}\n\n"
                        "Analyze and return JSON array only."
                    ),
                }],
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1500,
                priority="background",
            )

            content = (response.choices[0].message.content or "").strip()
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
            logger.error(f"[LLM] All providers failed for hourly analysis: {e}")
            if _response_cache["hourly_analysis"] is not None:
                logger.info("[LLM] Serving cached hourly analysis.")
                return _response_cache["hourly_analysis"]
            return []

    # ── Personalised hourly update ────────────────────────────────────────────

    async def generate_personalized_hourly_update(
        self,
        risk_preference: str,
        user_trades: list,
        yields: list,
        user_id: str = None,
    ) -> str:
        """
        Generates a personalised hourly Telegram message for a user.
        Called directly by scorer.py → HourlyScorer.run().
        """
        if not _PROVIDERS:
            return "⚠️ YieldSage background services are temporarily offline. Please check back later."

        # Parse user's risk preferences
        pref_tiers = [t.strip().lower() for t in risk_preference.split(",") if t.strip()]
        if not pref_tiers:
            pref_tiers = ["stable", "moderate", "aggressive"]

        # Filter yields per risk tier: Hard TVL > 10,000 filter, APY sort, max 15 per tier
        filtered_yields = []
        tier_counts = {}
        for tier in pref_tiers:
            tier_pools = [
                y for y in yields
                if (y.get("protocol") or {}).get("risk_tag", "").lower() == tier
            ]
            # Hard TVL exclusion: ignore dust/rug pools under $10k TVL
            tier_pools = [y for y in tier_pools if float(y.get("tvl_usd") or 0) > 10000]
            # Sort remainder by APY descending
            tier_pools.sort(key=lambda y: float(y.get("apy") or 0), reverse=True)
            
            top_tier = tier_pools[:15]
            filtered_yields.extend(top_tier)
            tier_counts[tier] = len(top_tier)

        tier_log_str = ", ".join(f"{t}={cnt}" for t, cnt in tier_counts.items())
        logger.info(f"[Yield Filter] User {user_id}: {tier_log_str}")

        # Build the authoritative URL map for this user's hourly update.
        # Only real pool_address values (cleaned) end up here.
        allowed_pool_url_map: dict = {}
        yield_context = ""
        for y in filtered_yields:
            p         = y.get("protocol", {})
            apy_val   = y.get("apy")
            tvl_val   = y.get("tvl_usd")
            apy_str   = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
            tvl_str   = f"${tvl_val:,.0f}" if tvl_val else "N/A"
            risk_tag  = p.get("risk_tag") or "unknown"
            url       = clean_pool_url(p.get("pool_address"))
            name_key  = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
            if url:
                allowed_pool_url_map[name_key] = url
                if p.get("name"):
                    allowed_pool_url_map[p.get("name").lower()] = url
                yield_context += (
                    f"- [{p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')})]({url}): "
                    f"APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
                )
            else:
                yield_context += (
                    f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): "
                    f"APY: {apy_str} | TVL: {tvl_str} | Risk: {risk_tag.upper()}\n"
                )

        # Get latest recommendations from database matching risk preference
        recs_context = ""
        if supabase:
            try:
                recs_data = []
                if pref_tiers:
                    for tier in pref_tiers:
                        # Get latest 3 recommendations for this tier
                        res = supabase.table("recommendations")\
                            .select("*, protocols(*)")\
                            .eq("risk_tag", tier)\
                            .order("created_at", desc=True)\
                            .limit(3)\
                            .execute()
                        if res.data:
                            # Sort by rank
                            sorted_recs = sorted(res.data, key=lambda x: x.get("rank", 99))
                            recs_data.extend(sorted_recs)
                
                if recs_data:
                    recs_context = "Selected On-chain Yield Recommendations (Ranked by priority):\n"
                    for r in recs_data:
                        p = r.get("protocols") or {}
                        apy_val = r.get("apy_at_time")
                        # Try to find corresponding TVL from yields list
                        tvl_val = None
                        if yields:
                            for y in yields:
                                if y.get("protocol_id") == r.get("protocol_id"):
                                    tvl_val = y.get("tvl_usd")
                                    break
                        apy_str = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
                        tvl_str = f"${tvl_val:,.0f}" if tvl_val else "N/A"
                        url = clean_pool_url(p.get("pool_address"))
                        rec_name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                        if url:
                            allowed_pool_url_map[rec_name_key] = url
                            if p.get("name"):
                                allowed_pool_url_map[p.get("name").lower()] = url
                        tx_hash = r.get("on_chain_tx_hash")
                        tx_str = f" | [Verify and take action](https://yieldsageai.xyz/verify?tx={tx_hash})" if tx_hash else ""

                        if url:
                            recs_context += (
                                f"- [{p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')})]({url}): "
                                f"APY: {apy_str} | TVL: {tvl_str} | Risk: {r['risk_tag'].upper()}{tx_str}\n"
                                f"  Reason: {r.get('ai_reasoning')}\n"
                            )
                        else:
                            recs_context += (
                                f"- {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}): "
                                f"APY: {apy_str} | TVL: {tvl_str} | Risk: {r['risk_tag'].upper()}{tx_str}\n"
                                f"  Reason: {r.get('ai_reasoning')}\n"
                            )
            except Exception as e:
                logger.error(f"Failed to fetch recommendations for hourly update: {e}")

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
                trade_name_key = f"{p.get('name', '')} {p.get('pool_name', '')}".strip().lower()
                if url:
                    allowed_pool_url_map[trade_name_key] = url
                    if p.get("name"):
                        allowed_pool_url_map[p.get("name").lower()] = url
                    trade_context += (
                        f"- Protocol: [{p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')})]({url}) | "
                        f"Entry APY: {t['entry_apy']:.2f}% | "
                        f"Current APY: {apy_str} | "
                        f"Current Investment: ${t['simulated_investment_usd']:.2f}\n"
                    )
                else:
                    trade_context += (
                        f"- Protocol: {p.get('name', 'Unknown')} ({p.get('pool_name', 'Unknown')}) | "
                        f"Entry APY: {t['entry_apy']:.2f}% | "
                        f"Current APY: {apy_str} | "
                        f"Current Investment: ${t['simulated_investment_usd']:.2f}\n"
                    )
        else:
            trade_context = "User has NO active paper trades right now.\n"

        system_prompt = f"""You are YieldSage's autonomous DeFi research and advisory agent. You write professional hourly Telegram broadcast messages for DeFi users on Solana.
{_DATA_INTEGRITY_BLOCK}
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
Every single pool name that has an EXACT address in the context MUST be a Markdown link.
Copy the link EXACTLY as it appears in the context — never construct or guess an address.
FORMAT → [Protocol Name](exact_url_from_context)
WRONG → Kamino USDC pool offers 8.5% APY  ← when context has a link for it
RIGHT → [Kamino USDC](https://solscan.io/account/ByYiZxp8QrdN9qbdtaAiePN8AAr3qvTPppNJDpf5DVJ5) offers 8.5% APY  ← copy exactly from context
If a pool appears in the context WITHOUT a link, write its name as plain text — never invent a URL.

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

LAW 8 ── ALL SNAPSHOT RECOMMENDATIONS MUST INCLUDE THEIR EXACT PROOF LINK.
You must include the exact Verify and take action link provided at the end of the pool details line.
FORMAT → | [Verify and take action](https://yieldsageai.xyz/verify?tx=0x...)
WRONG → • [Kamino USDC](...): **8.50% APY** | TVL: $142M | STABLE
RIGHT → • [Kamino USDC](...): **8.50% APY** | TVL: $142M | STABLE | [Verify and take action](https://yieldsageai.xyz/verify?tx=2FaU1EagECiz6tByzrXgGHq1p4xuW5ggd4doPFp5HJaxLEkn7LwvNMcuEZU2bfC63ujMcr5jcWe6RWGyzyS6n4cx)

LAW 9 ── INTELLIGENT SPLITTING FOR LONG MESSAGES.
If your report will be very long (e.g. analyzing 4+ active positions), you MUST intelligently split the report into separate message parts. Between each part, place the exact separator token: <<<PART_BREAK>>> on its own line. Rules for splitting:
- Each part must be independently readable, complete sentences, and perfectly formatted.
- Every Markdown link [text](url) must be fully closed within the same part — never split a link across parts.
- Every bold **text** must be opened and closed within the same part.
- Place the break at a natural boundary (end of a section or between bullet points).
- NEVER place the break mid-sentence, mid-link, or mid-bullet.
- The timestamp and CTA footer will be automatically appended to your last part — do NOT add it yourself.

════════════════════════════════════════
MANDATORY OUTPUT STRUCTURE — FOLLOW EXACTLY
════════════════════════════════════════

📊 **Solana Yield Snapshots & Recommendations**
[2-3 bullets of selected yield recommendations matching the user's risk preference — each on its OWN line]
[Each bullet MUST include the pool link, APY, TVL, risk, and proof link from Selected On-chain Yield Recommendations context. Do not invent any values!]
[Consistently append "Reason: [AI Reasoning from context]" at the end of each bullet on the same line, exactly as shown in the example.]

💼 **Personalized Portfolio Analysis**
[You MUST analyze and list EVERY SINGLE trade in the User's Active Paper Trades context. Do not omit, group, or skip any of them. For EACH trade, output exactly one bullet point formatted as follows:
• [Protocol Name (Pool Name)](exact_url_from_context_if_available): Entry X.XX% APY → Current Y.YY% APY [Status symbol/text] — [Detailed personalized analysis of this position, specifically checking for performance changes, yield sustainability, pool risk, TVL shifts, and whether it is underperforming by 2%+ or outperforming, with actionable advice].
  CRITICAL: Only use the URL that appears in the context data. If no URL is in the context for this pool, write the name as plain text — no link.

For status symbols/text:
- If underperforming by 2%+: ⚠️ Underperforming by Z.ZZ%
- If performing normally or close (within 2%): 🟢 Steady
- If outperforming: ✅ Outperforming

If the user has NO active trades (User has NO active paper trades right now), suggest paper trading benefits and recommend one specific pool matching their risk preference to start with.]

💡 **Actionable DeFi Intelligence**
[One senior-engineer-level Solana DeFi insight from the live data]

════════════════════════════════════════
FORMAT EXAMPLE — COPY THIS STRUCTURE EXACTLY
════════════════════════════════════════

📊 **Solana Yield Snapshots & Recommendations**

• [Kamino USDC](https://solscan.io/account/ByYiZxp8QrdN9qbdtaAiePN8AAr3qvTPppNJDpf5DVJ5): **8.50% APY** | TVL: $142,000,000 | STABLE | [Verify and take action](https://yieldsageai.xyz/verify?tx=2FaU1EagECiz6tByzrXgGHq1p4xuW5ggd4doPFp5HJaxLEkn7LwvNMcuEZU2bfC63ujMcr5jcWe6RWGyzyS6n4cx) Reason: Largest lending vault on Solana. Highest stable-tier yield right now.

• [MarginFi USDC](https://solscan.io/account/2s37akK2eyBbp8DZgCm7RtsaEz8eJP3Nxd4urLHQv7yB): **7.20% APY** | TVL: $89,000,000 | STABLE | [Verify and take action](https://yieldsageai.xyz/verify?tx=GtLfBLTi8Uzqg9iAdcK1DHp4ovQTMsVMr1KqyBJzmyevRq4pVRkD8HBUwNgvZSx38mcqFnuDR6qbqcKL1SzLqjM) Reason: Battle-tested. Lowest counterparty risk on Solana.

💼 **Personalized Portfolio Analysis**

• [Kamino USDC](https://solscan.io/account/ByYiZxp8QrdN9qbdtaAiePN8AAr3qvTPppNJDpf5DVJ5): Entry 8.50% APY → Current 8.20% APY 🟢 Steady — minor APY dip of 0.30%, hold position.

💡 **Actionable DeFi Intelligence**

Kamino USDC remains the deepest stable vault on Solana. Minor APY fluctuation due to deposit inflows. No rebalancing needed yet.

════════════════════════════════════════
OUTPUT CONSTRAINTS
════════════════════════════════════════
- Portfolio Analysis completeness: You MUST include every single active trade in the portfolio. Never summarize them into a single line or say "and others". Each trade gets its own bullet and its own dedicated paragraph of detailed analysis and reasons.
- Length: Be precise and direct — no padding. Every sentence must add information. No preamble. No sign-off. Start directly with 📊. Do not worry about Telegram's character limits as our delivery engine automatically handles splitting and paginating long messages cleanly.
- Risk profile: {risk_preference.upper()} — only recommend matching pools.
- ALL numerical values (APY, TVL, investment amounts) must come from LIVE DATA. Never invent.
- ZERO HALLUCINATION OF EXAMPLE DATA: The pools, APYs, TVLs, transaction hashes (tx), and reasoning shown in the FORMAT EXAMPLE section are for structural reference only. Under NO circumstances should you output any details from the examples (such as Kamino USDC at 8.50%, transaction signature 2FaU1EagECiz6tByzrXgGHq1p4xuW5ggd4doPFp5HJaxLEkn7LwvNMcuEZU2bfC63ujMcr5jcWe6RWGyzyS6n4cx, etc.) unless they are explicitly present in the live database context provided to you. If a pool or trade is not in the user's active trades or the live yield snapshot, you must never mention it.

════════════════════════════════════════
MANDATORY SELF-CHECK BEFORE RESPONDING
════════════════════════════════════════
1. Starts with 📊 **Solana Yield Snapshots & Recommendations**
2. All three sections present
3. Zero # headers — only **bold** titles
4. Zero | tables — only bullets
5. Every pool with address = [Name](url) link
6. No raw underscores
7. Bold = **double asterisks**
8. Every bullet on its own line with blank line before it
9. Every recommendation includes the correct Verify and take action link format at the end
10. Every APY, TVL, and Verify and take action value matches the context exactly — not invented

Fix any failure before responding.
"""

        # ── TOKEN GUARD CHECK ────────────────────────────────────────────────
        user_prompt_content = (
            f"{recs_context}\n\n"
            f"Live yield data:\n{yield_context}\n\n"
            f"User trades:\n{trade_context}\n\n"
            "Generate the hourly Telegram update now. "
            "Start IMMEDIATELY with 📊 **Solana Yield Snapshots & Recommendations** — "
            "no introduction, no preamble. "
            "Use the Selected On-chain Yield Recommendations list above for Section 1, including their Proof links exactly. "
            "Use ONLY APY and TVL values from the live data above. "
            "All pool links as [Name](url). Bold = **double asterisks**. No # headers. "
            "CRITICAL: Be concise but complete. Analyze every active position."
        )
        full_payload_str = system_prompt + user_prompt_content
        estimated_tokens = len(full_payload_str) // 4

        logger.info(f"[Token Guard] User {user_id} prompt size: ~{estimated_tokens} tokens ({len(full_payload_str)} chars)")
        if estimated_tokens > 6000:
            err_msg = f"[Token Guard] 🚨 PROMPT OVERFLOW: Prompt token estimate ({estimated_tokens}) exceeds 6,000 limit!"
            logger.error(err_msg)
            raise ValueError(err_msg)

        try:
            response = await _llm_call(
                messages=[{"role": "user", "content": user_prompt_content}],
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=6000,
                priority="background",
            )

            # Return RAW LLM content — do NOT call clean_telegram_markdown here.
            # broadcast_alerts_job splits on <<<PART_BREAK>>> first, then cleans each
            # chunk individually to prevent double-escaping of underscores in links.
            result = (response.choices[0].message.content or "").strip()

            # ── Strip any hallucinated or unmapped pool links from LLM output ──
            result = enforce_authentic_pool_links(result, allowed_pool_url_map)

            # ── Append UTC timestamp and CTA ──
            utc_now = datetime.utcnow()
            timestamp_line = (
                f"\n\n\U0001f550 Data snapshot: "
                f"{utc_now.strftime('%d %b %Y \u00b7 %H:%M UTC')}"
            )
            cta_line = "\n\n\U0001f4cb View all live yield opportunities on Solana \u2192 /yields or [yieldsageai.xyz/dashboard](https://yieldsageai.xyz/dashboard)"
            result = result + timestamp_line + cta_line

            # Cache in RAM per user
            if user_id:
                _response_cache["hourly_updates"][user_id] = result
            return result

        except Exception as e:
            logger.error(f"[LLM] All providers failed for hourly update (user {user_id}): {e}")
            
            # 1. Check in-memory RAM cache first
            cached = _response_cache["hourly_updates"].get(user_id) if user_id else None
            
            # 2. If RAM cache is missing (e.g. after container restart), query Supabase DB persistent fallback
            if not cached and user_id and supabase:
                try:
                    db_cache = supabase.table("telegram_messages")\
                        .select("content, created_at, sent_at")\
                        .eq("user_id", user_id)\
                        .eq("status", "sent")\
                        .order("created_at", desc=True)\
                        .limit(1)\
                        .execute()
                    if db_cache.data and db_cache.data[0].get("content"):
                        row = db_cache.data[0]
                        msg_time_str = row.get("sent_at") or row.get("created_at")
                        is_fresh = False
                        if msg_time_str:
                            try:
                                msg_dt = datetime.fromisoformat(msg_time_str.replace("Z", "+00:00"))
                                age_seconds = (datetime.now(timezone.utc) - msg_dt).total_seconds()
                                if age_seconds < 3 * 3600:  # Less than 3 hours old
                                    is_fresh = True
                                else:
                                    logger.info(f"[LLM Cache] Persistent DB fallback for user {user_id} is stale ({age_seconds/3600:.1f}h old > 3h max). Ignoring.")
                            except Exception as parse_err:
                                logger.warning(f"[LLM Cache] Could not parse message timestamp '{msg_time_str}': {parse_err}")

                        if is_fresh:
                            cached = row["content"]
                            # Strip any previous cached note before re-appending
                            if "\n\n_⚠️ Cached — AI busy." in cached:
                                cached = cached.split("\n\n_⚠️ Cached — AI busy.")[0]
                            _response_cache["hourly_updates"][user_id] = cached
                            logger.info(f"[LLM Cache] Restored fresh (<3h old) DB fallback for user {user_id}")
                except Exception as db_err:
                    logger.warning(f"[LLM Cache] DB persistent fallback lookup error: {db_err}")

            if cached:
                return (
                    cached
                    + "\n\n_⚠️ Cached — AI busy. Fresh update coming next hour._"
                )
            return (
                "⚠️ Sorry, I had trouble generating your hourly market update. "
                "I will try again next hour!"
            )

    async def generate_dashboard_picks(self, yields) -> list:
        """
        Selects top 3 yields for stable, moderate, and aggressive risk tags,
        and saves them to the recommendations table in Supabase.
        """
        if not supabase or not yields:
            logger.error("Supabase not available or yields list empty.")
            return []

        import json
        import hashlib

        # Build candidate list for LLM
        candidates = []
        for i, y in enumerate(yields):
            p = y.get("protocol") or {}
            candidates.append({
                "index": i,
                "protocol": p.get("name") or "Unknown",
                "pool_name": p.get("pool_name") or "Unknown",
                "asset": y.get("asset") or "Unknown",
                "apy": y.get("apy") or 0.0,
                "tvl_usd": y.get("tvl_usd") or 0.0,
                "risk_tag": (p.get("risk_tag") or "stable").lower()
            })

        candidates_str = json.dumps(candidates, indent=2)

        system_prompt = f"""You are YieldSage, a professional DeFi yield strategist on Solana.
Your task is to select the top 3 best yield opportunities for each of the three risk tiers: 'stable', 'moderate', and 'aggressive' from the provided candidates.

For each tier, rank the picks as 1 (best/top priority), 2 (second best), and 3 (third best) based on their yield vs risk tradeoffs, TVL liquidity, and protocol reputability.
If a tier has fewer than 3 candidates, you may output fewer than 3 picks for that tier, but aim for 3 if candidates are available.

Provide a short, professional, data-backed reasoning (1-2 sentences) for each pick.

Output your response STRICTLY as a valid JSON object matching the following structure:
{{
  "stable": [
    {{ "index": 0, "rank": 1, "reasoning": "Fluxion offers the highest stable yields with deep liquidity." }},
    ...
  ],
  "moderate": [
    ...
  ],
  "aggressive": [
    ...
  ]
}}

Ensure that the indices you select correspond EXACTLY to the index in the candidates list.
{_DATA_INTEGRITY_BLOCK}
"""

        try:
            # Set scored_at BEFORE calling the LLM cascade
            scored_at = datetime.now(timezone.utc)

            response = await _llm_call(
                messages=[{
                    "role": "user",
                    "content": f"Live yield candidate data:\n{candidates_str}\n\nSelect the top picks and output as a valid JSON object matching the requested structure.",
                }],
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=2000,
                priority="background",
            )

            content = (response.choices[0].message.content or "").strip()
            model_used = getattr(response, "model", "AI Cascade")

            # Clean markdown code block wrappers
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n", "", content)
                content = re.sub(r"\n```$", "", content)
                content = content.strip()

            picks_data = json.loads(content)

            from logger import build_recommendation_payload, log_recommendation_onchain, hash_payload

            inserted_recs = []
            for tier in ["stable", "moderate", "aggressive"]:
                picks = picks_data.get(tier, [])
                for pick in picks:
                    idx = pick.get("index")
                    rank = pick.get("rank")
                    reasoning = pick.get("reasoning")
                    if idx is None or rank is None or reasoning is None:
                        continue
                    if idx < 0 or idx >= len(yields):
                        continue

                    y = yields[idx]
                    protocol_id = y["protocol_id"]
                    apy_at_time = y.get("apy") or 0.0

                    p = y.get("protocol") or {}
                    protocol_name = p.get("name") or "Unknown"
                    pool_name = p.get("pool_name") or "Unknown"
                    pool_address = p.get("pool_address") or ""
                    tvl_usd = y.get("tvl_usd") or 0.0

                    # 1. Build the canonical payload and compute hash BEFORE inserting to DB
                    #    so recommendation_hash (NOT NULL) is always set on insert.
                    payload = build_recommendation_payload(
                        protocol_name = protocol_name,
                        pool_name      = pool_name,
                        pool_address   = pool_address,
                        risk_tag       = tier,
                        rank           = rank,
                        apy_at_time    = apy_at_time,
                        tvl_usd        = tvl_usd,
                        ai_reasoning   = reasoning,
                        ai_model       = model_used,
                        scored_at      = scored_at,
                    )
                    rec_hash = hash_payload(payload)

                    # 2. Insert to DB with hash already set; on_chain_tx_hash stays null until logged
                    insert_result = supabase.table("recommendations").insert({
                        "protocol_id":         protocol_id,
                        "risk_tag":            tier,
                        "rank":                rank,
                        "apy_at_time":         apy_at_time,
                        "tvl_usd":             tvl_usd,
                        "ai_reasoning":        reasoning,
                        "ai_model":            model_used,
                        "recommendation_hash": rec_hash,
                        "on_chain_tx_hash":    None,
                        "on_chain_logged_at":  None,
                        "created_at":          scored_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                    }).execute()

                    if not insert_result.data:
                        logger.error(f"Failed to insert recommendation for {protocol_name} in DB.")
                        continue

                    rec_id = insert_result.data[0]["id"]

                    # 3. Log on-chain (with retry) — returns (tx_hash, rec_hash)
                    tx_hash, _ = log_recommendation_onchain(payload)

                    # 4. If tx succeeded, update only the on-chain fields
                    if tx_hash:
                        supabase.table("recommendations").update({
                            "on_chain_tx_hash":   tx_hash,
                            "on_chain_logged_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", rec_id).execute()
                        logger.info(
                            f"[scorer] Recommendation {rec_id} on-chain. "
                            f"tx={tx_hash} hash={rec_hash[:12]}..."
                        )
                    else:
                        logger.info(
                            f"[scorer] Recommendation {rec_id} saved. "
                            f"On-chain log pending retry. hash={rec_hash[:12]}..."
                        )

                    inserted_recs.append(insert_result.data[0])

            return inserted_recs

        except Exception as e:
            logger.error(f"Failed to generate dashboard recommendations: {e}")
            return []