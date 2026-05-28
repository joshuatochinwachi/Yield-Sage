import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fetcher import DuneFetcher
from scorer import HourlyScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize persistent singletons
fetcher = DuneFetcher()
scorer = HourlyScorer()

async def run_pipeline():
    logger.info("Starting scheduled Yield-Sage pipeline...")
    
    # 1. Fetch Dune yields with retries for transient errors
    max_retries = 3
    retry_delay = 30  # seconds
    fetch_success = False
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Running Dune Fetcher (attempt {attempt}/{max_retries})...")
            await fetcher.run()
            fetch_success = True
            logger.info("Dune Fetcher completed successfully.")
            break
        except Exception as e:
            logger.error(f"Dune Fetcher failed on attempt {attempt}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying Fetcher in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                
    if not fetch_success:
        logger.error("Dune Fetcher failed after all attempts. Skipping Scoring Engine for this hour.")
        return

    # 2. Run Scorer to evaluate paper trades against updated yields and queue alerts
    try:
        logger.info("Running Hourly AI Scoring Engine...")
        await scorer.run()
        logger.info("Hourly AI Scoring Engine completed successfully.")
    except Exception as e:
        logger.error(f"Hourly Scoring Engine failed with exception: {e}")

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # Run immediately on startup, then every 1 hour
    scheduler.add_job(run_pipeline, 'interval', hours=1, id="pipeline_job", next_run_time=datetime.now())
    
    scheduler.start()
    logger.info("APScheduler started. Pipeline job running now, then every 1 hour.")
    
    # Keep the main thread alive if run independently
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    start_scheduler()
