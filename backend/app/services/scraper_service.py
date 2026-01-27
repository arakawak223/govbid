import asyncio
import logging
from datetime import datetime
from typing import Type

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bid
from app.scrapers.base import BaseScraper, BidInfo
from app.scrapers.fukuoka_pref import FukuokaPrefScraper
from app.scrapers.fukuoka_city import FukuokaCityScraper
from app.scrapers.kitakyushu import KitakyushuScraper
from app.scrapers.kurume import KurumeScraper
from app.scrapers.tagawa import TagawaScraper
from app.scrapers.munakata import MunakataScraper
from app.scrapers.omuta import OmutaScraper
from app.scrapers.iizuka import IizukaScraper
from app.scrapers.fukutsu import FukutsuScraper
from app.scrapers.yanagawa import YanagawaScraper
from app.scrapers.saga import SagaScraper
from app.scrapers.saga_city import SagaCityScraper
from app.scrapers.karatsu import KaratsuScraper
from app.scrapers.tosu import TosuScraper
from app.scrapers.imari import ImariScraper
from app.scrapers.takeo import TakeoScraper
from app.scrapers.arita import AritaScraper
from app.scrapers.nagasaki import NagasakiScraper
from app.scrapers.nagasaki_city import NagasakiCityScraper
from app.scrapers.sasebo import SaseboScraper
from app.scrapers.isahaya import IsahayaScraper
from app.scrapers.omura import OmuraScraper
from app.scrapers.shimabara import ShimabaraScraper
from app.scrapers.goto import GotoScraper
from app.scrapers.tsushima import TsushimaScraper
from app.scrapers.kumamoto_pref import KumamotoPrefScraper
from app.scrapers.kumamoto_city import KumamotoCityScraper
from app.scrapers.yatsushiro import YatsushiroScraper
from app.scrapers.amakusa import AmakusaScraper
from app.scrapers.tamana import TamanaScraper
from app.scrapers.aso import AsoScraper
from app.scrapers.hitoyoshi import HitoyoshiScraper
from app.scrapers.kikuyo import KikuyoScraper
from app.scrapers.oita import OitaScraper
from app.scrapers.oita_city import OitaCityScraper
from app.scrapers.beppu import BeppuScraper
from app.scrapers.nakatsu import NakatsuScraper
from app.scrapers.hita import HitaScraper
from app.scrapers.saiki import SaikiScraper
from app.scrapers.usuki import UsukiScraper
from app.scrapers.yufu import YufuScraper
from app.scrapers.miyazaki import MiyazakiScraper
from app.scrapers.miyazaki_city import MiyazakiCityScraper
from app.scrapers.miyakonojo import MiyakonojoScraper
from app.scrapers.nobeoka import NobeokaScraper
from app.scrapers.hyuga import HyugaScraper
from app.scrapers.nichinan import NichinanScraper
from app.scrapers.takachiho import TakachihoScraper
from app.scrapers.kagoshima import KagoshimaScraper
from app.scrapers.kagoshima_city import KagoshimaCityScraper
from app.scrapers.kirishima import KirishimaScraper
from app.scrapers.kanoya import KanoyaScraper
from app.scrapers.satsumasendai import SatsumasendaiScraper
from app.scrapers.ibusuki import IbusukiScraper
from app.scrapers.amami import AmamiScraper
from app.scrapers.hioki import HiokiScraper
from app.scrapers.okinawa import OkinawaScraper
from app.scrapers.naha_city import NahaCityScraper
from app.scrapers.okinawa_city import OkinawaCityScraper
from app.scrapers.nago import NagoScraper
from app.scrapers.urasoe import UrasoeScraper
from app.scrapers.yamaguchi import YamaguchiScraper
from app.scrapers.yamaguchi_city import YamaguchiCityScraper
from app.services.filter_service import filter_bids

logger = logging.getLogger(__name__)

# All available scrapers
SCRAPERS: list[Type[BaseScraper]] = [
    # 福岡県
    FukuokaPrefScraper,
    FukuokaCityScraper,
    KitakyushuScraper,
    KurumeScraper,
    TagawaScraper,
    MunakataScraper,
    OmutaScraper,
    IizukaScraper,
    FukutsuScraper,
    YanagawaScraper,
    # 佐賀県
    SagaScraper,
    SagaCityScraper,
    KaratsuScraper,
    TosuScraper,
    ImariScraper,
    TakeoScraper,
    AritaScraper,
    # 長崎県
    NagasakiScraper,
    NagasakiCityScraper,
    SaseboScraper,
    IsahayaScraper,
    OmuraScraper,
    ShimabaraScraper,
    GotoScraper,
    TsushimaScraper,
    # 熊本県
    KumamotoPrefScraper,
    KumamotoCityScraper,
    YatsushiroScraper,
    AmakusaScraper,
    TamanaScraper,
    AsoScraper,
    HitoyoshiScraper,
    KikuyoScraper,
    # 大分県
    OitaScraper,
    OitaCityScraper,
    BeppuScraper,
    NakatsuScraper,
    HitaScraper,
    SaikiScraper,
    UsukiScraper,
    YufuScraper,
    # 宮崎県
    MiyazakiScraper,
    MiyazakiCityScraper,
    MiyakonojoScraper,
    NobeokaScraper,
    HyugaScraper,
    NichinanScraper,
    TakachihoScraper,
    # 鹿児島県
    KagoshimaScraper,
    KagoshimaCityScraper,
    KirishimaScraper,
    KanoyaScraper,
    SatsumasendaiScraper,
    IbusukiScraper,
    AmamiScraper,
    HiokiScraper,
    # 沖縄県
    OkinawaScraper,
    NahaCityScraper,
    OkinawaCityScraper,
    NagoScraper,
    UrasoeScraper,
    # 山口県
    YamaguchiScraper,
    YamaguchiCityScraper,
]


async def _scrape_municipality(
    scraper_class: Type[BaseScraper],
    semaphore: asyncio.Semaphore
) -> dict:
    """Run a single scraper with semaphore for concurrency control

    Args:
        scraper_class: The scraper class to run
        semaphore: Semaphore to limit concurrency

    Returns:
        Dict with scraping results for this municipality
    """
    async with semaphore:
        scraper = scraper_class()
        municipality = scraper.municipality_name

        try:
            logger.info(f"Starting scrape for {municipality}")

            # Run the scraper
            raw_bids = await scraper.scrape()

            # Filter for relevant bids
            filtered_bids = filter_bids(raw_bids)

            logger.info(
                f"Completed {municipality}: {len(raw_bids)} scraped, "
                f"{len(filtered_bids)} filtered"
            )

            return {
                "municipality": municipality,
                "raw_bids": raw_bids,
                "filtered_bids": filtered_bids,
                "error": None,
            }

        except Exception as e:
            error_msg = f"Error scraping {municipality}: {str(e)}"
            logger.error(error_msg)
            return {
                "municipality": municipality,
                "raw_bids": [],
                "filtered_bids": [],
                "error": error_msg,
            }

        finally:
            await scraper.close()


async def run_all_scrapers(db: AsyncSession) -> dict:
    """Run all scrapers in parallel and save results to database

    Args:
        db: Database session

    Returns:
        Summary of scraping results
    """
    # Delete all existing bids before fresh scrape
    await db.execute(delete(Bid))
    await db.commit()
    logger.info("Cleared existing bids for fresh scrape")

    results = {
        "total_scraped": 0,
        "total_filtered": 0,
        "total_new": 0,
        "municipalities": {},
        "errors": [],
    }

    # Run scrapers in parallel with concurrency limit of 5
    semaphore = asyncio.Semaphore(5)
    tasks = [
        _scrape_municipality(scraper_class, semaphore)
        for scraper_class in SCRAPERS
    ]

    logger.info(f"Starting parallel scrape of {len(SCRAPERS)} municipalities (5 concurrent)")
    scrape_results = await asyncio.gather(*tasks)

    # Process results and save to database
    for scrape_result in scrape_results:
        municipality = scrape_result["municipality"]

        if scrape_result["error"]:
            results["errors"].append(scrape_result["error"])
            continue

        raw_bids = scrape_result["raw_bids"]
        filtered_bids = scrape_result["filtered_bids"]

        results["total_scraped"] += len(raw_bids)
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
        f"Parallel scrape complete: {results['total_scraped']} scraped, "
        f"{results['total_filtered']} filtered, {results['total_new']} new"
    )

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
            # Delete existing bids for this municipality before scrape
            await db.execute(delete(Bid).where(Bid.municipality == municipality))
            await db.commit()
            logger.info(f"Cleared existing bids for {municipality}")

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


EXCLUDE_KEYWORDS = [
    # 写真募集系
    "写真の募集",
    "写真募集",
    "フォトコンテスト",
    # 職場体験・インターン系
    "職場体験の募集",
    "職場体験の実施及び受入事業所の募集",
    "ジョブシャドウイング",
    "インターンシップ受入",
    "受入事業所の募集",
    # 広告募集系
    "広告募集",
    "広告の募集",
    "広告掲載の募集",
    "広告枠の募集",
    # Q&A・質問回答系
    "質問および回答",
    "質問及び回答",
    "質問・回答",
    "質問と回答",
    "Q&A",
    "Ｑ＆Ａ",
    # その他除外
    "ボランティア募集",
    "参加者募集",
    "出店者募集",
    "出展者募集",
]


async def cleanup_unwanted_bids(db: AsyncSession) -> int:
    """Remove bids that match exclusion keywords from database.

    Returns:
        Number of bids deleted
    """
    deleted_count = 0

    for keyword in EXCLUDE_KEYWORDS:
        result = await db.execute(
            select(Bid).where(Bid.title.contains(keyword))
        )
        bids_to_delete = result.scalars().all()
        for bid in bids_to_delete:
            logger.info(f"Deleting unwanted bid: {bid.title[:50]}")
            await db.delete(bid)
            deleted_count += 1

    if deleted_count > 0:
        await db.commit()
        logger.info(f"Cleaned up {deleted_count} unwanted bids")

    return deleted_count


async def save_bids(db: AsyncSession, bids: list[BidInfo]) -> int:
    """Save bids to database, avoiding duplicates

    Args:
        db: Database session
        bids: List of BidInfo objects

    Returns:
        Number of new bids saved
    """
    # First, cleanup any unwanted bids
    await cleanup_unwanted_bids(db)

    new_count = 0

    # Get current max bid_number
    result = await db.execute(select(func.max(Bid.bid_number)))
    current_max = result.scalar() or 0

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
            # Create new bid with bid_number
            current_max += 1
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
                bid_number=current_max,
            )
            db.add(new_bid)
            new_count += 1

    await db.commit()
    return new_count


def get_municipality_names() -> list[str]:
    """Get list of all supported municipality names"""
    return [scraper.municipality_name for scraper in SCRAPERS]
