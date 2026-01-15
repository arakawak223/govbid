import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.scraper_service import run_all_scrapers
from app.services.notification_service import send_new_bids_notification

settings = get_settings()
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_scrape_job():
    """Job that runs on schedule to scrape all municipalities"""
    logger.info(f"Starting scheduled scrape at {datetime.utcnow()}")

    async with AsyncSessionLocal() as db:
        try:
            results = await run_all_scrapers(db)

            logger.info(
                f"Scheduled scrape completed: "
                f"{results['total_scraped']} scraped, "
                f"{results['total_filtered']} filtered, "
                f"{results['total_new']} new"
            )

            # Send notifications for new bids
            if results['total_new'] > 0:
                # Get the new bids for notification
                from sqlalchemy import select
                from app.models import Bid

                # Get bids added in the last hour (approximation for "new")
                from datetime import timedelta
                cutoff = datetime.utcnow() - timedelta(hours=1)

                result = await db.execute(
                    select(Bid).where(Bid.created_at >= cutoff)
                )
                new_bids = result.scalars().all()

                if new_bids:
                    emails_sent = await send_new_bids_notification(db, list(new_bids))
                    logger.info(f"Sent {emails_sent} notification emails")

        except Exception as e:
            logger.error(f"Error in scheduled scrape: {e}")


def start_scheduler():
    """Start the background scheduler"""
    # Run daily at 6:00 AM JST (21:00 UTC previous day)
    scheduler.add_job(
        scheduled_scrape_job,
        CronTrigger(hour=21, minute=0),  # 6:00 AM JST
        id="daily_scrape",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started - daily scrape scheduled for 6:00 AM JST")


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
