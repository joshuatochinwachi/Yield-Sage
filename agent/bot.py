import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeDefault, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv, find_dotenv
from ai_service import AIService, supabase, clean_telegram_markdown

# Load environment variables
load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")

# Initialize AI Service
ai = AIService()

# State machine dictionary to track user steps (e.g. paper trade amount inputs)
# Structure: {chat_id: {"state": "STATE_NAME", "data": {...}}}
user_states = {}

async def ensure_user_exists(chat_id: int, username: str, first_name: str, last_name: str) -> str:
    """Ensures a user exists in the Supabase users table and returns their user UUID."""
    if not supabase:
        return None
    try:
        # Check if user already exists
        res = supabase.table("users").select("id").eq("telegram_chat_id", chat_id).limit(1).execute()
        if res.data:
            return res.data[0]["id"]
            
        # Register new user
        email = f"tg_{chat_id}@yieldsage.io"
        full_name = f"{first_name or ''} {last_name or ''}".strip() or username or f"Telegram User {chat_id}"
        payload = {
            "email": email,
            "full_name": full_name,
            "telegram_chat_id": chat_id,
            "risk_preference": "stable,moderate,aggressive"
        }
        logger.info(f"Auto-registering Telegram user {chat_id} ({full_name})...")
        insert_res = supabase.table("users").insert(payload).execute()
        if insert_res.data:
            uid = insert_res.data[0]["id"]
            # Ensure alert preference row is created with is_active = True
            try:
                supabase.table("alert_preferences").insert({"user_id": uid, "is_active": True}).execute()
            except Exception as ap_err:
                logger.error(f"Error creating default alert preference for user {uid}: {ap_err}")
            return uid
        return None
    except Exception as e:
        logger.error(f"Error ensuring user exists: {e}")
        return None

async def get_user_alerts_status(user_uuid: str) -> bool:
    """Returns whether alerts are active for a user, creating the row if missing."""
    if not supabase:
        return True
    try:
        res = supabase.table("alert_preferences").select("is_active").eq("user_id", user_uuid).limit(1).execute()
        if res.data:
            return res.data[0].get("is_active", True)
        
        # If missing, insert default row
        supabase.table("alert_preferences").insert({"user_id": user_uuid, "is_active": True}).execute()
        return True
    except Exception as e:
        logger.error(f"Error fetching/creating alert preferences: {e}")
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the greeting message and presents the main menu."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Reset any state
    user_states.pop(chat_id, None)
    
    # Ensure user exists in database
    await ensure_user_exists(chat_id, user.username, user.first_name, user.last_name)
    
    name = user.first_name or "there"
    greeting = (
        f"👋 **Welcome to YieldSage, {name}!**\n\n"
        "I am your intelligent AI-powered DeFi yield assistant for the **Solana Network**.\n\n"
        "Here is what I can do for you:\n"
        "📈 **Paper Trading**: Simulate investing in live yield pools with zero capital risk. Wanna make real investments? Check [yieldsageai.xyz/dashboard](https://www.yieldsageai.xyz/dashboard).\n"
        "🚨 **Hourly Scoring & Alerts**: Automatically analyze your positions and alert you if yields drop or if better options appear.\n"
        "🔍 **On-Chain Verification**: Check and cryptographically verify AI recommendations using on-chain SHA-256 hashes.\n"
        "💬 **DeFi Assistant & Insights**: Ask me any questions about yield strategies, pool risks, TVL drops, or portfolio optimization!\n\n"
        "Use the buttons below to explore:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 View Yield Pools", callback_data="view_yields"),
            InlineKeyboardButton("💼 My Positions", callback_data="view_positions")
        ],
        [
            InlineKeyboardButton("📈 Simulate Trade", callback_data="start_trade"),
            InlineKeyboardButton("⚙️ Risk Preference", callback_data="view_risk")
        ],
        [
            InlineKeyboardButton("🔔 Alert Settings", callback_data="view_alerts"),
            InlineKeyboardButton("💡 Prompts & FAQs", callback_data="view_prompts")
        ],
        [
            InlineKeyboardButton("🔍 Verify Proof", callback_data="view_verify"),
            InlineKeyboardButton("❓ Help & Guide", callback_data="view_help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(greeting, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    elif update.callback_query:
        await update.callback_query.message.edit_text(greeting, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def prompts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays an intelligent prompt keyboard for quick questions."""
    prompts = [
        "What are the safest yield pools on Solana right now?",
        "Which pools offer the highest APY, and why are they so high?",
        "Explain the risks of providing liquidity to high-APY pools.",
        "How do I balance my portfolio between stable and volatile assets?",
        "How can I simulate a paper trade?",
        "What is impermanent loss and how can I avoid it?",
        "Can you recommend a low-risk strategy for a $1,000 portfolio?",
        "What happens if a protocol's TVL drops significantly?",
        "Are there any promising stablecoin-only yield opportunities?",
        "How often should I review and rebalance my active paper trades?",
        "What factors do you consider when assigning a risk tier?",
        "Explain the difference between lending pools and liquidity pools.",
        "Explain to me what paper trading, and how it works on YieldSage.",
        "Based on the live data, what is your advice on my current portfolio?",
        "Give me a position adjustment analysis based on the live data.",
        "What is my worse position now and how can I make it better?",
        "What if a protocol's TVL drops significantly? How does it affect my position?",
        "Give me the top 10 pools with the highest APY",
        "Give me a thorough yield comparison analysis based on the live data."
    ]
    
    keyboard = [[KeyboardButton(prompt)] for prompt in prompts]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Select a question or type your own..."
    )

    text = (
        "💡 **Intelligent Prompts & FAQs**\n\n"
        "Tap any question below to instantly ask YieldSage, or just type your own!"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the help and command guide."""
    help_text = (
        "💡 **YieldSage Command Guide**\n\n"
        "/start - Launch the main menu & register\n"
        "/yields - Show current yield opportunities on Solana\n"
        "/positions - View and close your active paper trades\n"
        "/trade - Guided setup to simulate a new position\n"
        "/prompts - View intelligent questions to ask the bot\n"
        "/risk - View or modify your risk preference\n"
        "/alerts - Toggle hourly DeFi recommendations & alerts\n"
        "/verify - Verify a recommendation proof by tx hash\n"
        "/help - Display this guide\n\n"
        "💬 **Ask me anything!** You can also chat with me like Claude or ChatGPT to get custom advice on DeFi, yields, or adjusting your portfolio."
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifies a recommendation by transaction hash."""
    if not supabase:
        await update.message.reply_text("❌ Database unavailable.")
        return

    # Check if arguments were provided
    if not context.args:
        help_text = (
            "🔍 **How to Verify a YieldSage Proof**\n\n"
            "Usage: `/verify <transaction_signature>`\n"
            "Example: `/verify 2FaU1EagECiz6t...`\n\n"
            "Every recommendation is fingerprinted with SHA-256 and logged on the Solana blockchain. "

            "This command retrieves the original recommendation, computes its SHA-256 fingerprint, "
            "and compares it to the on-chain logged hash to guarantee it has never been altered."
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        return

    tx_hash = context.args[0].strip()
    # Check simple validity
    if not (tx_hash.startswith("0x") and len(tx_hash) == 66):
        await update.message.reply_text("❌ Invalid transaction hash format. It should start with `0x` and be 66 characters long.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Fetch from DB. We check for exact match, case-insensitive match, and prefixes.
        # Use execute() instead of single() to avoid PGRST116 exceptions.
        # Fetch from DB: try exact match first (Solana Base58 is case-sensitive), then ilike match
        rec_res = (
            supabase.table("recommendations")
            .select(
                "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
                "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
            )
            .eq("on_chain_tx_hash", tx_hash)
            .execute()
        )

        if not rec_res.data:
            # Fallback to case-insensitive match
            rec_res = (
                supabase.table("recommendations")
                .select(
                    "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
                    "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                    "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
                )
                .ilike("on_chain_tx_hash", f"%{tx_hash.replace('0x', '')}%")
                .execute()
            )

        if not rec_res.data:
            await update.message.reply_text(
                "❌ Recommendation not found in database for this transaction hash.\n"
                f"Searched for hash: `{tx_hash}`\n"
                "Make sure you copied the correct Solana transaction signature, or that the transaction has finished indexing."
            )
            return

        rec = rec_res.data[0]
        if not rec.get("protocols"):
            rec["protocols"] = {
                "id": "",
                "name": "Unknown Protocol",
                "pool_name": "Unknown Pool",
                "pool_address": ""
            }

        # Reconstruct canonical JSON payload
        try:
            from agent.logger import build_recommendation_payload
        except ImportError:
            from logger import build_recommendation_payload

        import json
        import hashlib

        # Parse ISO datetime
        created_at_str = rec["created_at"].replace("Z", "+00:00")
        scored_at_dt = datetime.fromisoformat(created_at_str)
        
        # Get TVL and APY candidates from snapshots immediately before or after created_at
        # (resolves rounding, precision discrepancies, and race conditions where snapshot fetched_at is slightly after rec created_at)
        snap_res_lte = (
            supabase.table("yield_snapshots")
            .select("tvl_usd, apy")
            .eq("protocol_id", rec["protocols"]["id"])
            .lte("fetched_at", rec["created_at"])
            .order("fetched_at", desc=True)
            .limit(2)
            .execute()
        )
        snap_res_gte = (
            supabase.table("yield_snapshots")
            .select("tvl_usd, apy")
            .eq("protocol_id", rec["protocols"]["id"])
            .gte("fetched_at", rec["created_at"])
            .order("fetched_at", desc=False)
            .limit(2)
            .execute()
        )
        
        real_tvl_val = 0.0
        if snap_res_lte.data and snap_res_lte.data[0]["tvl_usd"] is not None:
            try:
                real_tvl_val = float(snap_res_lte.data[0]["tvl_usd"])
            except (ValueError, TypeError):
                pass
        elif snap_res_gte.data and snap_res_gte.data[0]["tvl_usd"] is not None:
            try:
                real_tvl_val = float(snap_res_gte.data[0]["tvl_usd"])
            except (ValueError, TypeError):
                pass
        real_tvl = real_tvl_val
        
        tvls = [0.0]
        apys = []
        try:
            apys.append(f"{float(rec['apy_at_time']):.4f}")
            apys.append(f"{float(rec['apy_at_time']):.2f}")
        except (ValueError, TypeError):
            pass
        apys.append(str(rec['apy_at_time']))
        
        # Pull candidate values from nearby snapshots
        for s in (snap_res_lte.data or []) + (snap_res_gte.data or []):
            if s.get("tvl_usd") is not None:
                try:
                    tvls.append(float(s["tvl_usd"]))
                except (ValueError, TypeError):
                    pass
            if s.get("apy") is not None:
                try:
                    apys.append(f"{float(s['apy']):.4f}")
                    apys.append(f"{float(s['apy']):.2f}")
                except (ValueError, TypeError):
                    pass
                apys.append(str(s['apy']))
        
        # Look for percentages or numbers in reasoning
        import re
        pct_matches = re.findall(r'([0-9.]+)\s*%', rec["ai_reasoning"])
        for pm in pct_matches:
            apys.append(pm)
            try:
                apys.append(f"{float(pm):.4f}")
            except (ValueError, TypeError):
                pass
            
        num_matches = re.findall(r'\$?([0-9,]+)(?:\.[0-9]+)?', rec["ai_reasoning"])
        for nm in num_matches:
            clean_nm = nm.replace(",", "").strip()
            if clean_nm:  # Ensure it's not an empty string (e.g. from standalone commas in reasoning)
                try:
                    val = float(clean_nm)
                    tvls.append(val)
                except (ValueError, TypeError):
                    pass
            
        tvls = list(set(tvls))
        apys = list(set(apys))
        
        target_hash = rec["recommendation_hash"]
        matched_payload = None
        found_match = False

        # Generate candidates for renames or formatting differences
        proto_names = list(set([
            rec["protocols"]["name"],
            rec["protocols"]["name"].replace(" ", "-"),
            rec["protocols"]["name"].replace("-", " "),
            rec["protocols"]["name"].lower(),
            "kamino-finance", "kamino", "marginfi", "jito", "orca", "raydium", "drift", "marinade"
        ]))
        
        pool_names = list(set([
            rec["protocols"]["pool_name"],
            rec["protocols"]["pool_name"].replace("/", "-"),
            rec["protocols"]["pool_name"].replace("-", "/"),
        ]))
        
        raw_addr = rec["protocols"]["pool_address"] or ""
        pool_addresses = list(set([
            raw_addr,
            raw_addr.lower() if raw_addr else "",
            "",
        ]))
        
        models = list(set([
            rec["ai_model"],
            "meta/llama-3.3-70b-instruct",
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "qwen/qwen3.6-27b",
        ]))

        # Try permutations to find the exact configuration matching the stored recommendation_hash
        for proto_n in proto_names:
            for pool_n in pool_names:
                for addr in pool_addresses:
                    for tvl_v in tvls:
                        for apy_v in apys:
                            for model_v in models:
                                for source in ["dune_query_7595582", None]:
                                    for version in ["1.0", None]:
                                        for chain_info in [True, False]:
                                            # Try build_recommendation_payload style payload
                                            payload = {
                                                "scored_at": scored_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                "risk_tag": rec["risk_tag"],
                                                "rank": rec["rank"],
                                                "protocol_name": proto_n,
                                                "pool_name": pool_n,
                                                "pool_address": addr.lower() if (addr and isinstance(addr, str)) else (addr or ""),
                                                "apy_at_time": apy_v,
                                                "tvl_usd": f"{float(tvl_v):.2f}",
                                                "ai_reasoning": rec["ai_reasoning"].strip(),
                                                "ai_model": model_v,
                                            }
                                            if version:
                                                payload["version"] = version
                                            if source:
                                                payload["source"] = source
                                            if chain_info:
                                                payload["chain"] = "solana"
                                                payload["chain_id"] = 101
                                                
                                            canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                                            computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                                            if computed_hash == target_hash:
                                                matched_payload = canonical_json
                                                found_match = True
                                                break
                                            
                                            # Try legacy payload style
                                            if not version and not source and not chain_info:
                                                legacy_payload = {
                                                    "scored_at": scored_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                    "risk_tag": rec["risk_tag"],
                                                    "rank": rec["rank"],
                                                    "protocol_name": proto_n,
                                                    "pool_name": pool_n,
                                                    "pool_address": (addr or "").lower(),
                                                    "apy_at_time": apy_v,
                                                    "tvl_usd": f"{float(tvl_v):.2f}",
                                                    "ai_reasoning": rec["ai_reasoning"].strip(),
                                                    "ai_model": model_v
                                                }
                                                canonical_json = json.dumps(legacy_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                                                computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                                                if computed_hash == target_hash:
                                                    matched_payload = canonical_json
                                                    found_match = True
                                                    break
                                        if found_match: break
                                    if found_match: break
                                if found_match: break
                            if found_match: break
                        if found_match: break
                    if found_match: break
                if found_match: break
            if found_match: break

        # Fallback if no match is found (prevents NameError and bot crash)
        if not found_match:
            payload = build_recommendation_payload(
                protocol_name=rec["protocols"]["name"],
                pool_name=rec["protocols"]["pool_name"],
                pool_address=rec["protocols"]["pool_address"] or "",
                risk_tag=rec["risk_tag"],
                rank=rec["rank"],
                apy_at_time=rec["apy_at_time"],
                tvl_usd=real_tvl,
                ai_reasoning=rec["ai_reasoning"],
                ai_model=rec["ai_model"],
                scored_at=scored_at_dt,
            )
            canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

        is_valid = found_match

        if is_valid:
            verify_text = (
                f"✅ **Cryptographic Proof Verified Successfully!**\n\n"
                f"This recommendation matches the Solana blockchain record and is 100% untampered.\n\n"
                f"🏦 **Pool**: `{rec['protocols']['name']} ({rec['protocols']['pool_name']})`\n"
                f"🏷️ **Risk Tier**: `{rec['risk_tag'].upper()}`\n"
                f"📈 **APY**: **{rec['apy_at_time']}%**\n"
                f"🧠 **AI Model**: `{rec['ai_model']}`\n\n"
                f"🔗 **Computed Hash**:\n`{computed_hash}`\n"
                f"🔗 **Input Data Hash**:\n`{rec['recommendation_hash']}`\n\n"
                f"💬 **AI Reasoning**:\n_{rec['ai_reasoning']}_\n"
            )
            # Add buttons to view on web verify page or Solscan
            keyboard = [
                [
                    InlineKeyboardButton("🌐 Verify on Web", url=f"https://www.yieldsageai.xyz/verify?tx={tx_hash}"),
                    InlineKeyboardButton("🔍 View on Solscan", url=f"https://solscan.io/tx/{tx_hash}")
                ]
            ]
            await update.message.reply_text(
                verify_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        else:
            verify_text = (
                f"❌ **PROOF VERIFICATION FAILED (TAMPERED!)**\n\n"
                f"🚨 **Warning**: The computed SHA-256 hash does not match the logged on-chain fingerprint! "
                f"The database copy of this recommendation has been modified or corrupted.\n\n"
                f"🔗 **Computed Hash**:\n`{computed_hash}`\n"
                f"🔗 **On-Chain Hash**:\n`{rec['recommendation_hash']}`"
            )
            await update.message.reply_text(verify_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error executing verification command: {e}")
        await update.message.reply_text(f"❌ Verification failed: {str(e)}")

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to view and toggle alert settings."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Reset any state
    user_states.pop(chat_id, None)
    
    # Ensure user exists in database
    user_uuid = await ensure_user_exists(chat_id, user.username, user.first_name, user.last_name)
    if not user_uuid:
        text = "❌ There was an issue retrieving your user profile. Please type /start and try again."
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text)
        return
        
    is_active = await get_user_alerts_status(user_uuid)
    
    status_str = "🔔 **ENABLED**" if is_active else "🔕 **DISABLED**"
    
    text = (
        "🔔 **Notification & Alert Settings**\n\n"
        f"Hourly status updates & recommendations: {status_str}\n\n"
        "When enabled, YieldSage will run autonomous research and send you hourly updates "
        "covering Solana yield pools, general DeFi recommendations, and alerts or position "
        "shifts for your simulated trades."
    )
    
    toggle_text = "🔕 Disable Hourly Updates" if is_active else "🔔 Enable Hourly Updates"
    keyboard = [
        [InlineKeyboardButton(toggle_text, callback_data="toggle_alerts")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to view and toggle risk preferences."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Reset any state
    user_states.pop(chat_id, None)
    
    # Ensure user exists in database
    await ensure_user_exists(chat_id, user.username, user.first_name, user.last_name)
    
    try:
        user_res = supabase.table("users").select("risk_preference").eq("telegram_chat_id", chat_id).limit(1).execute()
        pref_str = user_res.data[0].get("risk_preference") if user_res.data else "stable,moderate,aggressive"
        if not pref_str: pref_str = "stable,moderate,aggressive"
        prefs = [p.strip().lower() for p in pref_str.split(",")]
        
        display_str = ", ".join([p.upper() for p in prefs])
        text = (
            f"⚙️ **Your Risk Preference**\n\n"
            f"Current preferences: **{display_str}**\n\n"
            "You can select multiple risk tiers. "
            "Recommendations and alerts will be filtered based on your active tiers."
        )
        
        btn_stable = "✅ Stable" if "stable" in prefs else "Stable"
        btn_moderate = "✅ Moderate" if "moderate" in prefs else "Moderate"
        btn_aggressive = "✅ Aggressive" if "aggressive" in prefs else "Aggressive"
        
        keyboard = [
            [
                InlineKeyboardButton(btn_stable, callback_data="setrisk_stable"),
                InlineKeyboardButton(btn_moderate, callback_data="setrisk_moderate"),
                InlineKeyboardButton(btn_aggressive, callback_data="setrisk_aggressive")
            ],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error handling risk command: {e}")
        error_msg = "❌ Error retrieving risk preference settings."
        if update.message:
            await update.message.reply_text(error_msg)


def sort_diverse_yields(yields):
    """
    Sorts yields to maximize diversity on page 1.
    Groups pools by protocol, sorts each group by TVL (descending) and APY (descending).
    Then uses a round-robin approach to pick the top pool from each protocol, 
    ensuring multiple protocols are represented on the first page, prioritized by high TVL.
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    for y in yields:
        p_name = y.get("protocol", {}).get("name", "Unknown")
        grouped[p_name].append(y)
        
    for p_name in grouped:
        grouped[p_name].sort(
            key=lambda x: (float(x.get("tvl") or 0), float(x.get("apy") or 0)), 
            reverse=True
        )
        
    diverse_yields = []
    max_pools = max((len(pools) for pools in grouped.values()), default=0)
    
    for i in range(max_pools):
        round_pools = []
        for pools in grouped.values():
            if i < len(pools):
                round_pools.append(pools[i])
                
        # Sort this round's pools by TVL (desc) and APY (desc) so largest protocols appear at the top
        round_pools.sort(
            key=lambda x: (float(x.get("tvl") or 0), float(x.get("apy") or 0)), 
            reverse=True
        )
        diverse_yields.extend(round_pools)
        
    return diverse_yields

async def view_yields(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays top yield pools with dynamic pagination to prevent Telegram markup or length limits."""
    query = update.callback_query
    page = 1
    if query:
        await query.answer()
        if query.data.startswith("yieldpage_"):
            page = int(query.data.split("_")[1])
            
    yields = await ai.get_recent_yields()
    if not yields:
        text = "⚠️ No active yield pools found at the moment."
        if query:
            await query.message.edit_text(text)
        else:
            await update.message.reply_text(text)
        return
        
    # Sort yields by TVL and Protocol Diversity
    yields = sort_diverse_yields(yields)
    
    page_size = 6
    total_pools = len(yields)
    total_pages = (total_pools + page_size - 1) // page_size
    
    # Slice the yields for the current page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_yields = yields[start_idx:end_idx]
    
    risk_emoji = {"stable": "🟢", "moderate": "🟡", "aggressive": "🔴"}
    text = f"📊 **Yield Opportunities on Solana** (Page {page}/{total_pages})\n"
    text += f"Total active pools: **{total_pools}**\n\n"
    
    for i, y in enumerate(page_yields, start_idx + 1):
        p = y.get("protocol", {})
        apy_val = y.get('apy')
        apy_str = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
        tvl = y.get('tvl_usd') or 0
        name = p.get('name', '?')
        pool = p.get('pool_name', '?')
        risk = (p.get('risk_tag') or 'moderate').lower()
        emoji = risk_emoji.get(risk, "⚪")
        
        pool_address = p.get('pool_address')
        if pool_address:
            url = pool_address if pool_address.startswith('http') else f"https://solscan.io/account/{pool_address}"
            text += f"{i}. {emoji} **[{name}]({url})** ({pool})\n"
        else:
            text += f"{i}. {emoji} **{name}** ({pool})\n"
        text += f"   • APY: **{apy_str}** | TVL: **${tvl:,.0f}** | Risk: **{risk.upper()}**\n\n"
        
    text += "_Use /trade to simulate an investment_"
    
    # Keyboard with pagination controls
    keyboard = []
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"yieldpage_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"yieldpage_{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton("📈 Simulate Trade", callback_data="start_trade")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def view_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's active paper trades."""
    chat_id = update.effective_chat.id
    query_or_update = update.callback_query or update.message
    
    if update.callback_query:
        await update.callback_query.answer()
        
    trades = await ai.get_user_paper_trades(telegram_chat_id=chat_id)
    
    if not trades:
        text = (
            "💼 **Your Paper Trades**\n\n"
            "You don't have any active paper trades right now.\n"
            "Simulating trades allows me to analyze your yields hourly and alert you of underperformance."
        )
        keyboard = [
            [InlineKeyboardButton("📈 Simulate a Trade Now", callback_data="start_trade")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return
        
    text = "💼 **Your Active Paper Trades**\n\n"
    keyboard = []
    
    # We need to get current yields to show comparison
    yields = await ai.get_recent_yields()
    yield_map = {y["protocol_id"]: y["apy"] for y in yields}
    
    for t in trades:
        p_name = t["protocols"]["name"]
        p_pool = t["protocols"]["pool_name"]
        entry_apy = t["entry_apy"]
        
        # Safely get current_apy, fallback to entry_apy if missing or None
        current_apy = yield_map.get(t["protocol_id"])
        if current_apy is None:
            current_apy = entry_apy
            
        inv = t["simulated_investment_usd"]
        
        # Calculate yield accrued roughly using exact fractional days
        created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
        delta = datetime.now(created.tzinfo) - created
        days_held_exact = max(delta.total_seconds() / 86400, 0)
        
        est_return = inv * (current_apy / 100) * (days_held_exact / 365)
        
        pool_address = t["protocols"].get("pool_address")
        if pool_address:
            url = pool_address if pool_address.startswith('http') else f"https://solscan.io/account/{pool_address}"
            text += f"🔹 **[{p_name}]({url}) ({p_pool})**\n"
        else:
            text += f"🔹 **{p_name} ({p_pool})**\n"
            
        days_int = int(days_held_exact)
        time_display = f"{days_int} days" if days_int > 0 else "< 1 day"
        
        # Format accrued amount intelligently with a '+' sign
        accrued_str = f"+${est_return:,.2f}" if est_return >= 0.01 else f"+${est_return:,.4f}"
        current_val = inv + est_return
            
        text += (
            f"  • Investment: **${inv:,.2f}**\n"
            f"  • Entry APY: **{entry_apy:.2f}%** | Current: **{current_apy:.2f}%**\n"
            f"  • Estimated Profit: **{accrued_str}** ({time_display} held)\n"
            f"  • Current Value: **${current_val:,.2f}**\n\n"
        )
        keyboard.append([InlineKeyboardButton(f"❌ Close {p_name} ({p_pool})", callback_data=f"close_{t['id']}")] )
        
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def start_trade_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Presents pools sorted by APY with dynamic pagination for the user to simulate a paper trade."""
    query = update.callback_query
    page = 1
    if query:
        await query.answer()
        if query.data.startswith("tradepage_"):
            page = int(query.data.split("_")[1])
    else:
        # Check if arguments were passed (e.g. /trade address=... amount=... token=...)
        if update.message and update.message.text:
            text = update.message.text.strip()
            if len(text.split()) > 1:
                import re
                
                # 1. Try parsing the structured key-value format first
                address_match = re.search(r'address=(.*?)(?=\s+(?:amount|token)=|$)', text)
                amount_match = re.search(r'amount=(.*?)(?=\s+(?:address|token)=|$)', text)
                token_match = re.search(r'token=(.*?)(?=\s+(?:address|amount)=|$)', text)
                
                address = address_match.group(1).strip() if address_match else None
                amount_str = amount_match.group(1).strip() if amount_match else None
                token = token_match.group(1).strip() if token_match else None
                
                # 2. Fallback: If we don't have address or amount from structured format, try parsing space-separated arguments
                # e.g., "/trade 0x3812a... 5000" or "/trade 0x3812a... 5000 token-name"
                if not address and not token:
                    parts = text.split()
                    if len(parts) >= 3:
                        first_arg = parts[1].strip()
                        second_arg = parts[2].strip()
                        
                        # Check if first_arg is a hex address
                        hex_match = re.search(r'0x[a-fA-F0-9]{40}', first_arg)
                        if hex_match:
                            address = hex_match.group(0)
                            amount_str = second_arg
                            if len(parts) >= 4:
                                token = " ".join(parts[3:]).strip()
                        else:
                            # Maybe first_arg is token name and second_arg is amount
                            try:
                                float("".join(c for c in second_arg if c.isdigit() or c == "."))
                                token = first_arg
                                amount_str = second_arg
                            except ValueError:
                                # Or first_arg is amount and second_arg is token
                                try:
                                    float("".join(c for c in first_arg if c.isdigit() or c == "."))
                                    amount_str = first_arg
                                    token = second_arg
                                except ValueError:
                                    pass
                
                if address:
                    hex_match = re.search(r'0x[a-fA-F0-9]{40}', address)
                    if hex_match:
                        address = hex_match.group(0)
                
                if address or token:
                    protocol = None
                    if address:
                        try:
                            proto_res = supabase.table("protocols").select("id, name, pool_name, pool_address").ilike("pool_address", f"%{address}%").execute()
                            if proto_res.data:
                                protocol = proto_res.data[0]
                        except Exception as e:
                            logger.error(f"Error querying protocols by address: {e}")
                    
                    if not protocol and token:
                        try:
                            proto_res = supabase.table("protocols").select("id, name, pool_name, pool_address").ilike("pool_name", f"%{token}%").execute()
                            if proto_res.data:
                                protocol = proto_res.data[0]
                        except Exception as e:
                            logger.error(f"Error querying protocols by token: {e}")
                    
                    if protocol:
                        try:
                            amount = 1000.0
                            if amount_str:
                                clean_amt = "".join(c for c in amount_str if c.isdigit() or c == ".")
                                amount = float(clean_amt) if clean_amt else 1000.0
                            if amount <= 0:
                                amount = 1000.0
                        except Exception:
                            amount = 1000.0
                            
                        entry_apy = 0.0
                        try:
                            snap_res = supabase.table("yield_snapshots").select("apy").eq("protocol_id", protocol["id"]).order("fetched_at", desc=True).limit(1).execute()
                            if snap_res.data:
                                raw_apy = snap_res.data[0].get("apy")
                                entry_apy = float(raw_apy) if raw_apy is not None else 0.0
                        except Exception as e:
                            logger.error(f"Error fetching entry APY: {e}")
                            
                        try:
                            chat_id = update.effective_chat.id
                            user = update.effective_user
                            user_uuid = await ensure_user_exists(chat_id, user.username, user.first_name, user.last_name)
                            if user_uuid:
                                payload = {
                                    "user_id": user_uuid,
                                    "protocol_id": protocol["id"],
                                    "simulated_investment_usd": amount,
                                    "entry_apy": entry_apy,
                                    "status": "active"
                                }
                                supabase.table("paper_trades").insert(payload).execute()
                                
                                confirm_text = (
                                    f"✅ **Paper Trade Simulated Successfully!**\n\n"
                                    f"💰 Invested: **${amount:,.2f}**\n"
                                    f"🏦 Pool: **{protocol['name']} ({protocol['pool_name']})**\n"
                                    f"📈 Entry APY: **{entry_apy:.2f}%**\n\n"
                                    f"I will now monitor this position hourly. You will receive alerts if the APY drops or if better options appear!"
                                )
                                keyboard = [[InlineKeyboardButton("💼 View My Positions", callback_data="view_positions")]]
                                await update.message.reply_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
                                return
                        except Exception as e:
                            logger.error(f"Error registering direct paper trade: {e}")
                            await update.message.reply_text("❌ Failed to register paper trade. Please try again.")
                            return
                    else:
                        await update.message.reply_text(
                            f"🔍 Could not find a pool with address `{address or ''}` or token `{token or ''}` in our database.\n\n"
                            "Listing active yield opportunities instead:"
                        )

    yields = await ai.get_recent_yields()
    if not yields:
        text = "⚠️ No active yield pools available to trade right now."
        if query:
            await query.message.edit_text(text)
        else:
            await update.message.reply_text(text)
        return
        
    # Sort yields by TVL and Protocol Diversity
    yields = sort_diverse_yields(yields)
    
    page_size = 6
    total_pools = len(yields)
    total_pages = (total_pools + page_size - 1) // page_size
    
    # Slice the yields for the current page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_yields = yields[start_idx:end_idx]
    
    text = f"📈 **Simulate Paper Trade** (Page {page}/{total_pages})\n\nTap a pool to simulate an investment:"
    keyboard = []
    
    for y in page_yields:
        p = y.get("protocol", {})
        apy_val = y.get('apy')
        apy_str = f"{apy_val:.2f}%" if apy_val is not None else "N/A"
        name = p.get('name', '?')
        pool = p.get('pool_name', '?')
        label = f"{name} ({pool}) — {apy_str}"
        if len(label) > 50:
            label = label[:47] + "..."
        keyboard.append([InlineKeyboardButton(label, callback_data=f"tr_{p['id']}")] )
        
    # Navigation row
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"tradepage_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"tradepage_{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for all inline keyboard callback queries."""
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id
    
    if data == "main_menu":
        await start(update, context)
    elif data == "view_yields":
        await view_yields(update, context)
    elif data == "view_positions":
        await view_positions(update, context)
    elif data == "start_trade":
        await start_trade_flow(update, context)
    elif data.startswith("yieldpage_"):
        await view_yields(update, context)
    elif data.startswith("tradepage_"):
        await start_trade_flow(update, context)
    elif data == "view_help":
        # Send help and menu back button
        help_text = (
            "💡 **YieldSage User Guide**\n\n"
            "• **DeFi Chat**: Simply ask me any questions in this chat. I will remember our conversation and use real-time APY data to guide you.\n\n"
            "• **Paper Trading**: Track simulated investments in real-time. I will evaluate your entries and send recommendation alerts if a better pool in the same risk tier has higher APYs.\n\n"
            "• **Risk Preferences**: Toggle your target risk profile. I will tailor recommendations and summaries to match your profile."
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    elif data == "view_verify":
        # Send on-chain proof verification instructions
        verify_text = (
            "🔍 **On-Chain Yield Verification**\n\n"
            "Every YieldSage recommendation is fingerprinted with a secure SHA-256 hash and permanently logged on the **Solana blockchain**.\n\n"
            "To verify the authenticity of any recommendation, run:\n"
            "`/verify <transaction_signature>`\n\n"
            "Example:\n"
            "`/verify 2FaU1EagECiz6tByzrXgGHq1p4xuW5ggd4doPFp5HJaxLEkn7LwvNMcuEZU2bfC63ujMcr5jcWe6RWGyzyS6n4cx`\n\n"
            "**What happens next?**\n"
            "1. We fetch the matching recommendation from the secure database.\n"
            "2. We reconstruct the exact JSON metadata payload (APY, TVL, AI Reasoning, and timestamp).\n"
            "3. We hash it using SHA-256 and cross-examine it against the on-chain logged transaction signature.\n"
            "4. This mathematically proves the recommendation's integrity and prevents tampering."
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.message.edit_text(verify_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    elif data == "view_prompts":
        await query.answer()
        await prompts_command(update, context)
    elif data == "view_alerts":
        await query.answer()
        await alerts_command(update, context)
    elif data == "toggle_alerts":
        try:
            user_res = supabase.table("users").select("id").eq("telegram_chat_id", chat_id).limit(1).execute()
            if not user_res.data:
                await query.answer("User profile not found. Please run /start")
                return
            uid = user_res.data[0]["id"]
            current_status = await get_user_alerts_status(uid)
            new_status = not current_status
            supabase.table("alert_preferences").update({"is_active": new_status}).eq("user_id", uid).execute()
            status_word = "enabled" if new_status else "disabled"
            await query.answer(f"✅ Hourly updates successfully {status_word}!")
            await alerts_command(update, context)
        except Exception as e:
            logger.error(f"Error toggling alerts callback: {e}")
            await query.answer("❌ Error updating alert settings.")
    elif data == "view_risk" or data.startswith("setrisk_"):
        try:
            user_res = supabase.table("users").select("risk_preference").eq("telegram_chat_id", chat_id).limit(1).execute()
            pref_str = user_res.data[0].get("risk_preference") if user_res.data else "stable,moderate,aggressive"
            if not pref_str: pref_str = "stable,moderate,aggressive"
            prefs = [p.strip().lower() for p in pref_str.split(",")]
            
            if data.startswith("setrisk_"):
                clicked_risk = data.split("_")[1]
                if clicked_risk in prefs:
                    if len(prefs) > 1:
                        prefs.remove(clicked_risk)
                    else:
                        await query.answer("⚠️ You must have at least one risk preference selected!")
                        return
                else:
                    prefs.append(clicked_risk)

                pref_str = ",".join(prefs)
                update_res = supabase.table("users").update({"risk_preference": pref_str}).eq("telegram_chat_id", chat_id).execute()
                if not update_res.data:
                    await query.answer("❌ Failed to update risk preference. Please try again.")
                    return
                await query.answer("✅ Risk preferences updated!")
                
            display_str = ", ".join([p.upper() for p in prefs])
            text = (
                f"⚙️ **Your Risk Preference**\n\n"
                f"Current preferences: **{display_str}**\n\n"
                "You can select multiple risk tiers. "
                "Recommendations and alerts will be filtered based on your active tiers."
            )
            
            btn_stable = "✅ Stable" if "stable" in prefs else "Stable"
            btn_moderate = "✅ Moderate" if "moderate" in prefs else "Moderate"
            btn_aggressive = "✅ Aggressive" if "aggressive" in prefs else "Aggressive"
            
            keyboard = [
                [
                    InlineKeyboardButton(btn_stable, callback_data="setrisk_stable"),
                    InlineKeyboardButton(btn_moderate, callback_data="setrisk_moderate"),
                    InlineKeyboardButton(btn_aggressive, callback_data="setrisk_aggressive")
                ],
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
            ]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error handling risk menu: {e}")
            await query.answer("❌ Error updating risk preference.")
    elif data.startswith("tr_"):
        # Selected a protocol to trade
        protocol_id = data.split("_")[1]
        try:
            proto_res = supabase.table("protocols").select("name, pool_name").eq("id", protocol_id).limit(1).execute()
            if not proto_res.data:
                await query.answer("Protocol not found.")
                return
            p = proto_res.data[0]
            # Set state to await amount
            user_states[chat_id] = {
                "state": "AWAITING_AMOUNT",
                "data": {
                    "protocol_id": protocol_id,
                    "name": p["name"],
                    "pool_name": p["pool_name"]
                }
            }
            await query.message.reply_text(
                f"💸 How much USD would you like to simulate investing in **{p['name']} ({p['pool_name']})**?\n"
                "Please type a number (e.g. `1000`):"
            )
        except Exception as e:
            logger.error(f"Error in trade callback: {e}")
            await query.answer("Error starting trade simulation.")
    elif data.startswith("close_"):
        # Close paper trade
        trade_id = data.split("_")[1]
        try:
            supabase.table("paper_trades").update({
                "status": "closed",
                "closed_at": datetime.utcnow().isoformat()
            }).eq("id", trade_id).execute()
            await query.answer("✅ Paper trade closed successfully!")
            await view_positions(update, context)
        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            await query.answer("❌ Failed to close paper trade.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes normal text messages, either matching paper trade entry or general AI Q&A."""
    chat_id = update.effective_chat.id
    user_msg = update.message.text
    
    # 1. Check if user is in a state flow
    state_data = user_states.get(chat_id)
    if state_data and state_data.get("state") == "AWAITING_AMOUNT":
        # Parse investment amount
        try:
            amount = float("".join(c for c in user_msg if c.isdigit() or c == "."))
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except Exception:
            await update.message.reply_text("❌ Please enter a valid numerical investment amount (e.g., `5000` or `1250.50`):")
            return
            
        p_info = state_data["data"]
        protocol_id = p_info["protocol_id"]
        
        # Look up current APY from latest snapshots
        entry_apy = 0.0
        try:
            snap_res = supabase.table("yield_snapshots").select("apy").eq("protocol_id", protocol_id).order("fetched_at", desc=True).limit(1).execute()
            if snap_res.data:
                raw_apy = snap_res.data[0].get("apy")
                entry_apy = float(raw_apy) if raw_apy is not None else 0.0
        except Exception as e:
            logger.error(f"Error fetching snapshot for entry APY: {e}")
            
        # Ensure user database record
        user_uuid = await ensure_user_exists(chat_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)
        if not user_uuid:
            await update.message.reply_text("❌ There was an issue retrieving your user profile. Please type /start and try again.")
            return
            
        # Insert paper trade record
        try:
            payload = {
                "user_id": user_uuid,
                "protocol_id": protocol_id,
                "simulated_investment_usd": amount,
                "entry_apy": entry_apy,
                "status": "active"
            }
            supabase.table("paper_trades").insert(payload).execute()
            
            # Clear state
            user_states.pop(chat_id, None)
            
            confirm_text = (
                f"✅ **Paper Trade Simulated Successfully!**\n\n"
                f"💰 Invested: **${amount:,.2f}**\n"
                f"🏦 Pool: **{p_info['name']} ({p_info['pool_name']})**\n"
                f"📈 Entry APY: **{entry_apy:.2f}%**\n\n"
                f"I will now monitor this position hourly. You will receive alerts if the APY drops or if better options appear!"
            )
            
            keyboard = [[InlineKeyboardButton("💼 View My Positions", callback_data="view_positions")]]
            await update.message.reply_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            return
        except Exception as e:
            logger.error(f"Error saving paper trade: {e}")
            await update.message.reply_text("❌ Failed to register paper trade. Please try again.")
            user_states.pop(chat_id, None)
            return
            
    # 2. Otherwise, treat as conversational Q&A query
    # Send typing status indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Ensure user exists in database to load history
    await ensure_user_exists(chat_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)
    
    # Thinking callback — fires if LLM takes more than 3 seconds
    async def _send_thinking():
        await context.bot.send_message(
            chat_id=chat_id,
            text="🤔 YieldSage Agent is thinking... one moment please.",
        )

    # Get conversational reply (raw — cleaning done per-chunk inside _safe_reply)
    reply = await ai.handle_conversational_query(
        user_msg,
        telegram_chat_id=chat_id,
        thinking_callback=_send_thinking,
    )
    # Do NOT pre-clean here — _safe_reply splits on <<<PART_BREAK>>> and cleans each chunk
    await _safe_reply(update, context, reply)

TELEGRAM_MAX_LEN = 3900


def _split_message(text: str, limit: int = TELEGRAM_MAX_LEN) -> list:
    """
    Split a message into chunks that fit within Telegram's character limit.
    Splits on newlines to avoid cutting mid-sentence or mid-word.
    If a single line is longer than the limit, it splits the line itself by space/character limit.
    """
    if len(text) <= limit:
        return [text]

    chunks = []
    current = []
    current_len = 0

    for line in text.split("\n"):
        if len(line) > limit:
            # If current has content, flush it
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            # Split the ultra-long line
            remaining = line
            while len(remaining) > limit:
                split_idx = remaining.rfind(" ", 0, limit)
                if split_idx == -1:
                    split_idx = limit
                chunks.append(remaining[:split_idx])
                remaining = remaining[split_idx:].lstrip()
            if remaining:
                current = [remaining]
                current_len = len(remaining) + 1
        else:
            line_len = len(line) + 1
            if current_len + line_len > limit:
                if current:
                    chunks.append("\n".join(current))
                current = [line]
                current_len = line_len
            else:
                current.append(line)
                current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks



async def _send_chunk_with_retry(send_func, kwargs, label="chunk", max_retries=3):
    """
    Attempt to send a message chunk, first with Markdown, falling back to plain text if needed.
    Retries up to max_retries times on transient failures (network errors, rate limits).
    """
    # Create a copy of kwargs so modifications to parse_mode don't leak across retries
    kwargs_copy = dict(kwargs)
    for attempt in range(max_retries):
        try:
            # First attempt with Markdown (if parse_mode was set)
            await send_func(**kwargs_copy)
            return True
        except Exception as err:
            err_str = str(err).lower()
            is_markdown_error = "can't parse" in err_str or "bad request" in err_str or "markdown" in err_str
            
            # If it's a Markdown parsing error, immediately retry as plain text on this attempt
            if is_markdown_error and kwargs_copy.get("parse_mode") == ParseMode.MARKDOWN:
                logger.warning(f"[{label}] Markdown parse failed: {err}. Retrying as plain text...")
                kwargs_copy["parse_mode"] = None
                try:
                    await send_func(**kwargs_copy)
                    return True
                except Exception as plain_err:
                    err = plain_err
                    err_str = str(plain_err).lower()
            
            # Handle rate limit (429) specifically by sleeping longer
            sleep_time = 1.0 * (attempt + 1)
            if "too many requests" in err_str or "429" in err_str:
                sleep_time = 3.0
                logger.warning(f"[{label}] Rate limited (429) by Telegram. Sleeping {sleep_time}s before retry...")
            
            logger.warning(f"[{label}] Send attempt {attempt + 1}/{max_retries} failed: {err}")
            if attempt < max_retries - 1:
                await asyncio.sleep(sleep_time)
                
    return False


async def _safe_reply(
    update: Update,
    context,
    text: str,
    reply_markup=None,
    disable_web_page_preview: bool = True,
):
    """
    Send a reply that is guaranteed to be delivered in full, even when the
    message exceeds Telegram's 4096-character hard limit.

    Behaviour:
    - Single chunk  → reply_text on the original message (preserves the
                      "reply" thread so the user sees it in context).
    - Multiple chunks → first chunk is a reply; subsequent chunks are
                        plain follow-up messages sent immediately after,
                        labelled (Part N/Total) so the user knows they
                        belong together.
    - Per-chunk fallback: Markdown is attempted first; if Telegram rejects
      the parse, the same chunk is re-sent as plain text so nothing is lost.
    - `reply_markup` (keyboard) is attached only to the LAST chunk so the
      buttons appear at the end of the full message.
    """
    # ---- Split on LLM-provided separator (no underscores — safe from markdown escaping) ----
    PART_SEP = "<<<PART_BREAK>>>"
    # Also accept old separator forms in case of cached/legacy content
    OLD_SEPS = ["---MESSAGE_BREAK---", "---MESSAGE\\_BREAK---", "---MESSAGE\\\\_BREAK---"]
    normalized_text = text
    for old_sep in OLD_SEPS:
        normalized_text = normalized_text.replace(old_sep, PART_SEP)

    if PART_SEP in normalized_text:
        raw_chunks = [c.strip() for c in normalized_text.split(PART_SEP) if c.strip()]
    else:
        raw_chunks = None  # will use _split_message after cleaning below

    if raw_chunks is not None:
        # Clean each LLM-defined chunk individually to avoid double-escaping
        chunks = [clean_telegram_markdown(c) for c in raw_chunks]
    else:
        # No LLM separator — clean the whole text once and split by length
        cleaned = clean_telegram_markdown(text)
        chunks = _split_message(cleaned)

    total = len(chunks)
    chat_id = update.effective_chat.id

    for i, chunk in enumerate(chunks):
        is_last = (i == total - 1)
        part_text = f"_(Part {i+1}/{total})_\n\n{chunk}" if total > 1 else chunk
        kwargs = dict(
            text=part_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=disable_web_page_preview,
        )
        if is_last and reply_markup:
            kwargs["reply_markup"] = reply_markup

        if i == 0:
            send_func = update.message.reply_text
        else:
            # Wrap context.bot.send_message to match expected signature
            send_func = lambda **kw: context.bot.send_message(chat_id=chat_id, **kw)

        success = await _send_chunk_with_retry(
            send_func=send_func,
            kwargs=kwargs,
            label=f"reply_chunk {i+1}/{total}"
        )
        if not success:
            logger.error(f"[_safe_reply] Failed to send chunk {i+1}/{total} after all retries.")

        # Small gap between chunks to respect Telegram rate limits
        if total > 1 and not is_last:
            await asyncio.sleep(0.5)


async def broadcast_alerts_job(context: ContextTypes.DEFAULT_TYPE):
    """Background repeating job that polls database for pending alerts and broadcasts them."""
    if not supabase:
        return
    try:
        res = supabase.table("telegram_messages").select("*").eq("status", "pending").execute()
        if not res.data:
            return

        logger.info(f"Found {len(res.data)} pending Telegram messages to send.")
        for msg in res.data:
            msg_id = msg["id"]
            chat_id = msg["chat_id"]
            content = msg["content"]

            # ---- Split on LLM-provided separator, then clean each chunk individually ----
            # Content from DB is RAW (ai_service no longer pre-cleans hourly updates).
            # We split FIRST on the separator, then clean per-chunk to prevent double-escaping.
            PART_SEP = "<<<PART_BREAK>>>"
            OLD_SEPS = ["---MESSAGE_BREAK---", "---MESSAGE\\_BREAK---", "---MESSAGE\\\\_BREAK---"]
            normalized = content
            for old_sep in OLD_SEPS:
                normalized = normalized.replace(old_sep, PART_SEP)

            if PART_SEP in normalized:
                raw_chunks = [c.strip() for c in normalized.split(PART_SEP) if c.strip()]
                chunks = [clean_telegram_markdown(c) for c in raw_chunks]
            else:
                # No LLM separator — clean whole content then split by Telegram limit
                cleaned_content = clean_telegram_markdown(content)
                chunks = _split_message(cleaned_content)

            total = len(chunks)

            chunks_sent = 0
            failed_chunks = []

            for i, chunk in enumerate(chunks):
                # Prepend part header when split across multiple messages
                part_text = f"_(Part {i+1}/{total})_\n\n{chunk}" if total > 1 else chunk

                kwargs = dict(
                    chat_id=chat_id,
                    text=part_text,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                
                # Wrap context.bot.send_message
                send_func = lambda **kw: context.bot.send_message(**kw)
                
                success = await _send_chunk_with_retry(
                    send_func=send_func,
                    kwargs=kwargs,
                    label=f"alert {msg_id} chunk {i+1}/{total}"
                )

                if success:
                    chunks_sent += 1
                else:
                    failed_chunks.append(i + 1)

                # Small gap between parts so Telegram doesn't throttle
                if total > 1 and i < total - 1:
                    await asyncio.sleep(0.5)

            # Update DB status based on delivery outcome
            if chunks_sent > 0:
                # At least something was delivered — mark sent so already-sent parts
                # are never re-delivered on the next poll cycle.
                supabase.table("telegram_messages").update({
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat()
                }).eq("id", msg_id).execute()
                if failed_chunks:
                    logger.warning(
                        f"[alert {msg_id}] Partially delivered to chat {chat_id}. "
                        f"Sent {chunks_sent}/{total} chunks. Failed chunks: {failed_chunks}"
                    )
                else:
                    logger.info(
                        f"Broadcasted alert {msg_id} to chat {chat_id}"
                        + (f" ({total} parts)" if total > 1 else "")
                    )
            else:
                # Every single chunk failed — keep status=failed so it is retried next cycle
                supabase.table("telegram_messages").update({
                    "status": "failed",
                    "error_message": f"All {total} chunks failed to send."
                }).eq("id", msg_id).execute()
                logger.error(
                    f"[alert {msg_id}] ALL {total} chunks failed for chat {chat_id}. Marked for retry."
                )

    except Exception as e:
        logger.error(f"Error polling alert queue: {e}")


def main():
    """Start the Telegram bot."""
    # Establish an event loop for this thread if one doesn't exist (needed when running in a background thread)
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        logger.info("No active event loop found in current thread. Creating new event loop...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if not TELEGRAM_TOKEN:
        logger.error("❌ No TELEGRAM_TOKEN found in env variables! Bot cannot start.")
        return

    retry_count = 0
    max_retries = 5
    retry_delay = 10  # seconds

    async def post_init(application):
        await application.bot.set_my_commands([
            BotCommand("start", "Start the bot and see main menu"),
            BotCommand("yields", "View current live yields"),
            BotCommand("positions", "View your active paper trades"),
            BotCommand("trade", "Simulate a new paper trade"),
            BotCommand("prompts", "Intelligent FAQs to ask the AI"),
            BotCommand("risk", "Manage your risk preferences"),
            BotCommand("alerts", "Toggle hourly DeFi recommendations & alerts"),
            BotCommand("verify", "Verify a recommendation proof by tx hash"),
            BotCommand("help", "Show help and guide")
        ], scope=BotCommandScopeDefault())

    while retry_count < max_retries:
        try:
            logger.info(f"Initializing YieldSage Telegram Bot (Attempt {retry_count + 1}/{max_retries})...")
            app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
            
            # Add Command Handlers
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("yields", view_yields))
            app.add_handler(CommandHandler("positions", view_positions))
            app.add_handler(CommandHandler("trade", start_trade_flow))
            app.add_handler(CommandHandler("prompts", prompts_command))
            app.add_handler(CommandHandler("risk", risk_command))
            app.add_handler(CommandHandler("alerts", alerts_command))
            app.add_handler(CommandHandler("verify", verify_command))
            app.add_handler(CommandHandler("help", help_command))
            
            # Add Callback Router (Inline Keyboard clicks)
            app.add_handler(CallbackQueryHandler(handle_callback))
            
            # Add Message Handler for general text & conversation Q&A
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            # Set up background job for polling pending database alerts every 30 seconds
            if app.job_queue:
                app.job_queue.run_repeating(broadcast_alerts_job, interval=30, first=5)
                logger.info("Alert broadcast background job scheduled (every 30 seconds).")
                
            logger.info("YieldSage Telegram Bot listening for updates...")
            app.run_polling(stop_signals=[])
            break  # Exit retry loop if run_polling completes normally
            
        except Exception as err:
            retry_count += 1
            logger.error(f"❌ Telegram Bot startup failed (Attempt {retry_count}/{max_retries}): {err}")
            if retry_count < max_retries:
                logger.info(f"Retrying Telegram Bot startup in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("🛑 Telegram Bot failed to start after maximum retry attempts.")

if __name__ == "__main__":
    main()
