import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeDefault
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv, find_dotenv
from ai_service import AIService, supabase

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
            "risk_preference": "moderate"
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
        "I am your intelligent DeFi yield advisor for the **Mantle Network**.\n\n"
        "Here is what I can do for you:\n"
        "📈 **Paper Trading**: Simulate investing in yield pools and track APY changes.\n"
        "🚨 **Hourly Scoring**: Analyze your positions and alert you if yields drop or if better options appear.\n"
        "💬 **DeFi Assistant**: Ask me any questions about yield opportunities or adjusting your portfolio!\n\n"
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
            InlineKeyboardButton("❓ Help & Guide", callback_data="view_help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(greeting, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.message.edit_text(greeting, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the help and command guide."""
    help_text = (
        "💡 **YieldSage Command Guide**\n\n"
        "/start - Launch the main menu & register\n"
        "/yields - Show current yield opportunities on Mantle\n"
        "/positions - View and close your active paper trades\n"
        "/trade - Guided setup to simulate a new position\n"
        "/risk - View or modify your risk preference\n"
        "/alerts - Toggle hourly DeFi recommendations & alerts\n"
        "/help - Display this guide\n\n"
        "💬 **Ask me anything!** You can also chat with me like Claude or ChatGPT to get custom advice on DeFi, yields, or adjusting your portfolio."
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

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
        "covering Mantle yield pools, general DeFi recommendations, and alerts or position "
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
        
    # Sort all yields by APY descending
    yields.sort(key=lambda x: float(x.get('apy') or 0), reverse=True)
    
    page_size = 6
    total_pools = len(yields)
    total_pages = (total_pools + page_size - 1) // page_size
    
    # Slice the yields for the current page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_yields = yields[start_idx:end_idx]
    
    risk_emoji = {"stable": "🟢", "moderate": "🟡", "aggressive": "🔴"}
    text = f"📊 **Yield Opportunities on Mantle** (Page {page}/{total_pages})\n"
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
            text += f"{i}. {emoji} **[{name}](https://mantlescan.xyz/address/{pool_address})** ({pool})\n"
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
        
        # Calculate yield accrued roughly
        created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
        days_held = max((datetime.now(created.tzinfo) - created).days, 0)
        est_return = inv * (current_apy / 100) * (days_held / 365)
        
        pool_address = t["protocols"].get("pool_address")
        if pool_address:
            text += f"🔹 **[{p_name}](https://mantlescan.xyz/address/{pool_address}) ({p_pool})**\n"
        else:
            text += f"🔹 **{p_name} ({p_pool})**\n"
            
        text += (
            f"  • Investment: **${inv:,.2f}**\n"
            f"  • Entry APY: **{entry_apy}%** | Current: **{current_apy:.2f}%**\n"
            f"  • Estimated Accrued: **${est_return:.2f}** ({days_held} days held)\n\n"
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
            
    yields = await ai.get_recent_yields()
    if not yields:
        text = "⚠️ No active yield pools available to trade right now."
        if query:
            await query.message.edit_text(text)
        else:
            await update.message.reply_text(text)
        return
        
    # Sort by APY descending
    yields.sort(key=lambda x: float(x.get('apy') or 0), reverse=True)
    
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
    elif data == "view_risk":
        # Fetch current preference
        pref = "moderate"
        try:
            user_res = supabase.table("users").select("risk_preference").eq("telegram_chat_id", chat_id).limit(1).execute()
            if user_res.data:
                pref = user_res.data[0].get("risk_preference", "moderate")
        except Exception as e:
            logger.error(f"Error fetching user risk preference: {e}")
            
        text = (
            f"⚙️ **Your Risk Preference**\n\n"
            f"Current preference: **{pref.upper()}**\n\n"
            "Adjusting your preference tells me what level of yield risk you are comfortable with. "
            "Recommendations and alerts will be filtered based on your tier."
        )
        keyboard = [
            [
                InlineKeyboardButton("🟢 Stable", callback_data="setrisk_stable"),
                InlineKeyboardButton("🟡 Moderate", callback_data="setrisk_moderate"),
                InlineKeyboardButton("🔴 Aggressive", callback_data="setrisk_aggressive")
            ],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    elif data.startswith("setrisk_"):
        new_risk = data.split("_")[1]
        try:
            # Update user profile
            supabase.table("users").update({"risk_preference": new_risk}).eq("telegram_chat_id", chat_id).execute()
            await query.answer(f"✅ Risk preference set to {new_risk.upper()}!")
            # Refresh view
            await start(update, context)
        except Exception as e:
            logger.error(f"Error setting risk: {e}")
            await query.answer("❌ Error updating profile.")
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
    
    # Get conversational reply
    reply = await ai.handle_conversational_query(user_msg, telegram_chat_id=chat_id)
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def broadcast_alerts_job(context: ContextTypes.DEFAULT_TYPE):
    """Background repeating job that polls database for pending alerts and broadcasts them."""
    if not supabase:
        return
    try:
        # Fetch pending messages from database queue
        res = supabase.table("telegram_messages").select("*").eq("status", "pending").execute()
        if not res.data:
            return
            
        logger.info(f"Found {len(res.data)} pending Telegram messages to send.")
        for msg in res.data:
            msg_id = msg["id"]
            chat_id = msg["chat_id"]
            content = msg["content"]
            
            try:
                # Send text via Telegram Bot
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=content,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                
                # Mark as sent
                supabase.table("telegram_messages").update({
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat()
                }).eq("id", msg_id).execute()
                logger.info(f"Broadcasted alert {msg_id} to chat {chat_id}")
            except Exception as send_err:
                logger.error(f"Failed to send queued alert {msg_id} to chat {chat_id}: {send_err}")
                supabase.table("telegram_messages").update({
                    "status": "failed",
                    "error_message": str(send_err)
                }).eq("id", msg_id).execute()
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
            BotCommand("alerts", "Toggle hourly DeFi recommendations & alerts"),
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
            app.add_handler(CommandHandler("alerts", alerts_command))
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
