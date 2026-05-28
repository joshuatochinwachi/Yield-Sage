import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import job logic and bot startup
from scheduler import run_pipeline
from bot import main as run_telegram_bot

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# Store references for cleanup
_scheduler = None
_bot_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup and shutdown lifecycle for YieldSage."""
    global _scheduler, _bot_thread
    logger.info("Initializing YieldSage Agent background services...")

    # 1. Start APScheduler in the active event loop
    try:
        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            run_pipeline, 'interval', hours=1,
            id="pipeline_job", next_run_time=datetime.now()
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

    yield  # App is running

    # Shutdown
    logger.info("Shutting down YieldSage Agent services...")
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")


app = FastAPI(title="YieldSage Agent API", lifespan=lifespan)


@app.get("/")
def read_root():
    return {"status": "YieldSage Agent Running", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "scheduler_running": _scheduler is not None and _scheduler.running if _scheduler else False,
        "bot_alive": _bot_thread is not None and _bot_thread.is_alive() if _bot_thread else False,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    is_dev = os.getenv("RAILWAY_ENVIRONMENT") is None  # Local dev only
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=is_dev)
