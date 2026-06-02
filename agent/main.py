import logging
import threading
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import job logic and bot startup
from scheduler import run_pipeline
from bot import main as run_telegram_bot

# Import all API routers
from routers.yields import router as yields_router
from routers.protocols import router as protocols_router
from routers.recommendations import router as recommendations_router
from routers.stats import router as stats_router
from routers.user import router as user_router
from routers.paper_trades import router as paper_trades_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

# Store references for cleanup
_scheduler = None
_bot_thread = None


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup and shutdown lifecycle for YieldSage."""
    global _scheduler, _bot_thread
    logger.info("Initializing YieldSage Agent background services...")

    # 1. Start APScheduler in the active event loop
    try:
        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            run_pipeline,
            "interval",
            hours=1,
            id="pipeline_job",
            next_run_time=datetime.now(),
        )
        _scheduler.start()
        logger.info("APScheduler background tasks started successfully.")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")

    # 2. Start the Telegram Bot in a daemon thread
    try:
        _bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        _bot_thread.start()
        logger.info("Telegram Bot background thread started successfully.")
    except Exception as e:
        logger.error(f"Failed to start Telegram Bot thread: {e}")

    yield  # ── App is running ──────────────────────────────────────────────

    # Shutdown
    logger.info("Shutting down YieldSage Agent services...")
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="YieldSage API",
    description=(
        "Real-time DeFi yield intelligence for the Mantle network. "
        "Powers the YieldSage web dashboard and Telegram bot."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Strictly allow ONLY our frontend and local dev. No other origin can call this API.
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://yieldsageai.xyz",
    "https://www.yieldsageai.xyz",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(yields_router)
app.include_router(protocols_router)
app.include_router(recommendations_router)
app.include_router(stats_router)
app.include_router(user_router)
app.include_router(paper_trades_router)


# ── Core endpoints ────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def read_root():
    return {
        "service": "YieldSage API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "scheduler_running": (
            _scheduler is not None and _scheduler.running
            if _scheduler else False
        ),
        "bot_alive": (
            _bot_thread is not None and _bot_thread.is_alive()
            if _bot_thread else False
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    is_dev = os.getenv("RAILWAY_ENVIRONMENT") is None
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=is_dev)
