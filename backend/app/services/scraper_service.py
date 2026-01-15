import logging
from datetime import datetime
from typing import Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bid
from app.scrapers.base import BaseScraper, BidInfo
from app.scrapers.fukuoka_pref import FukuokaPrefScraper
from app.scrapers.fukuoka_city import FukuokaCityScraper
from app.scrapers.kitakyushu import KitakyushuScraper
from app.scrapers.saga import SagaScraper
from app.scrapers.nagasaki import NagasakiScraper
from app.scrapers.kumamoto_pref import KumamotoPrefScraper
from app.scrapers.kumamoto_city import KumamotoCityScraper
from app.scrapers.oita import OitaScraper
from app.scrapers.miyazaki import MiyazakiScraper
from app.scrapers.kagoshima import KagoshimaScraper
from app.scrapers.okinawa import OkinawaScraper
from app.scrapers.yamaguchi import YamaguchiScraper
from app.services.filter_service import filter_bids

logger = logging.getLogger(__name__)

# All available scrapers
SCRAPERS: list[Type[BaseScraper]] = [
    FukuokaPrefScraper,
    FukuokaCityScraper,
    KitakyushuScraper,
    SagaScraper,
    NagasakiScraper,
    KumamotoPrefScraper,
    KumamotoCityScraper,
    OitaScraper,
    MiyazakiScraper,
    KagoshimaScraper,
    OkinawaScraper,
    YamaguchiScraper,
]


async def run_all_scrapers(db: AsyncSession) -> dict:
    """Run all scrapers and save results to database

    Args:
        db: Database session

    Returns:
        Summary of scraping results
    """
    results = {
        "total_scraped": 0,
        "total_filtered": 0,
        "total_new": 0,
        "municipalities": {},
        "errors": [],
    }

    for scraper_class in SCRAPERS:
        scraper = scraper_class()
        municipality = scraper.municipality_name

        try:
            logger.info(f"Starting scrape for {municipality}")

            # Run the scraper
            raw_bids = await scraper.scrape()
            results["total_scraped"] += len(raw_bids)

            # Filter for relevant bids
            filtered_bids = filter_bids(raw_bids)
            results["total_filtered"] += len(filtered_bids)

            # Save to database
            new_count = await save_bids(db, filtered_bids)
            results["total_new"] += new_count

            results["municipalities"][municipality] = {
                "scraped": len(raw_bids),
                "filtered": len(filtered_bids),
                "new": new_count,
            }

            logger.info(
                f"Completed {municipality}: {len(raw_bids)} scraped, "
                f"{len(filtered_bids)} filtered, {new_count} new"
            )

        except Exception as e:
            error_msg = f"Error scraping {municipality}: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        finally:
            await scraper.close()

    return results


async def run_single_scraper(db: AsyncSession, municipality: str) -> dict:
    """Run a single scraper by municipality name

    Args:
        db: Database session
        municipality: Municipality name

    Returns:
        Scraping results
    """
    for scraper_class in SCRAPERS:
        if scraper_class.municipality_name == municipality:
            scraper = scraper_class()
            try:
                raw_bids = await scraper.scrape()
                filtered_bids = filter_bids(raw_bids)
                new_count = await save_bids(db, filtered_bids)

                return {
                    "municipality": municipality,
                    "scraped": len(raw_bids),
                    "filtered": len(filtered_bids),
                    "new": new_count,
                }
            finally:
                await scraper.close()

    raise ValueError(f"Unknown municipality: {municipality}")


async def save_bids(db: AsyncSession, bids: list[BidInfo]) -> int:
    """Save bids to database, avoiding duplicates

    Args:
        db: Database session
        bids: List of BidInfo objects

    Returns:
        Number of new bids saved
    """
    new_count = 0

    for bid_info in bids:
        # Check if this bid already exists (by title and municipality)
        result = await db.execute(
            select(Bid).where(
                Bid.title == bid_info.title,
                Bid.municipality == bid_info.municipality,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing bid
            existing.announcement_url = bid_info.announcement_url
            existing.category = bid_info.category
            existing.max_amount = bid_info.max_amount
            existing.period_start = bid_info.period_start
            existing.period_end = bid_info.period_end
            existing.application_start = bid_info.application_start
            existing.application_end = bid_info.application_end
            existing.status = bid_info.status
            existing.scraped_at = datetime.utcnow()
        else:
            # Create new bid
            new_bid = Bid(
                title=bid_info.title,
                municipality=bid_info.municipality,
                category=bid_info.category,
                max_amount=bid_info.max_amount,
                announcement_url=bid_info.announcement_url,
                period_start=bid_info.period_start,
                period_end=bid_info.period_end,
                application_start=bid_info.application_start,
                application_end=bid_info.application_end,
                status=bid_info.status,
                source_url=bid_info.source_url,
            )
            db.add(new_bid)
            new_count += 1

    await db.commit()
    return new_count


def get_municipality_names() -> list[str]:
    """Get list of all supported municipality names"""
    return [scraper.municipality_name for scraper in SCRAPERS]
