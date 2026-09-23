import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.scraper_service import run_all_scrapers
from app.services.notification_service import send_new_bids_notification
from app.services.winner_service import run_winner_extraction

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


async def scheduled_winner_extract_job():
    """月次で落札企業抽出を実行する（手動トリガーと同じコードパス）"""
    logger.info(f"Starting scheduled winner extraction at {datetime.utcnow()}")

    async with AsyncSessionLocal() as db:
        try:
            results = await run_winner_extraction(db)
            logger.info(
                f"Winner extraction completed: "
                f"{results['targets']} targets, "
                f"{results['extracted']} extracted, "
                f"{results['saved']} saved"
            )
        except Exception as e:
            logger.error(f"Error in scheduled winner extraction: {e}")


def start_scheduler():
    """Start the background scheduler"""
    # Run daily at 6:00 AM JST (21:00 UTC previous day)
    scheduler.add_job(
        scheduled_scrape_job,
        CronTrigger(hour=21, minute=0),  # 6:00 AM JST
        id="daily_scrape",
        replace_existing=True,
    )

    # 落札企業抽出は毎月15日 6:00 JST（日次スクレイプと時間帯を分けて負荷を分散）
    scheduler.add_job(
        scheduled_winner_extract_job,
        CronTrigger(day=14, hour=21, minute=0),  # = 毎月15日 6:00 JST (21:00 UTC on the 14th)
        id="monthly_winner_extract",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started - daily scrape at 6:00 AM JST, "
        "monthly winner extraction on the 15th at 6:00 AM JST"
    )


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
