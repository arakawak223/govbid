import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class BidInfo:
    """Scraped bid information"""
    title: str
    municipality: str
    announcement_url: str
    source_url: str
    category: Optional[str] = None
    max_amount: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    application_start: Optional[date] = None
    application_end: Optional[date] = None
    status: str = "募集中"


class BaseScraper(ABC):
    """Base class for municipality scrapers"""

    municipality_name: str = ""
    base_url: str = ""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        self.delay = settings.request_delay_seconds

    async def close(self):
        await self.client.aclose()

    async def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        try:
            await asyncio.sleep(self.delay)
            response = await self.client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse various Japanese date formats"""
        if not date_str:
            return None

        import re
        date_str = date_str.strip()

        # Convert full-width numbers to half-width
        full_to_half = str.maketrans('０１２３４５６７８９', '0123456789')
        date_str = date_str.translate(full_to_half)

        # Common formats
        formats = [
            "%Y年%m月%d日",
            "%Y/%m/%d",
            "%Y-%m-%d",
            "%Y.%m.%d",
            "令和%Y年%m月%d日",
        ]

        # Handle 令和 (Reiwa era) - supports formats like "令和8年1月28日" or "令和8年（2026年）1月28日"
        if "令和" in date_str:
            match = re.search(r'令和(\d+)年[^月]*?(\d+)月(\d+)日', date_str)
            if match:
                year = int(match.group(1)) + 2018  # 令和1年 = 2019年
                month = int(match.group(2))
                day = int(match.group(3))
                try:
                    return date(year, month, day)
                except ValueError:
                    pass

        # Handle western year format: 2026年1月28日
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                pass

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def parse_amount(self, amount_str: str) -> Optional[int]:
        """Parse amount string to integer"""
        if not amount_str:
            return None

        import re
        amount_str = amount_str.strip()

        # Convert full-width numbers to half-width
        full_to_half = str.maketrans('０１２３４５６７８９，', '0123456789,')
        amount_str = amount_str.translate(full_to_half)

        # Handle 億 (100,000,000)
        if "億" in amount_str:
            match = re.search(r'([\d,.]+)\s*億', amount_str)
            if match:
                num = float(match.group(1).replace(",", ""))
                return int(num * 100_000_000)

        # Handle 万 (10,000)
        if "万" in amount_str:
            match = re.search(r'([\d,.]+)\s*万', amount_str)
            if match:
                num = float(match.group(1).replace(",", ""))
                return int(num * 10_000)

        # Handle 千 (1,000) - e.g., "7,800千円"
        if "千" in amount_str:
            match = re.search(r'([\d,]+)\s*千', amount_str)
            if match:
                num = float(match.group(1).replace(",", ""))
                return int(num * 1_000)

        # Extract numeric value
        match = re.search(r'([\d,]+)', amount_str)
        if match:
            return int(match.group(1).replace(",", ""))

        return None

    @abstractmethod
    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from the municipality website

        Returns:
            List of BidInfo objects
        """
        pass
