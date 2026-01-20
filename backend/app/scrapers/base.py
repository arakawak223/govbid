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

        date_str = date_str.strip()

        # Common formats
        formats = [
            "%Y年%m月%d日",
            "%Y/%m/%d",
            "%Y-%m-%d",
            "%Y.%m.%d",
            "令和%Y年%m月%d日",
        ]

        # Handle 令和 (Reiwa era)
        if "令和" in date_str:
            import re
            match = re.search(r'令和(\d+)年(\d+)月(\d+)日', date_str)
            if match:
                year = int(match.group(1)) + 2018  # 令和1年 = 2019年
                month = int(match.group(2))
                day = int(match.group(3))
                try:
                    return date(year, month, day)
                except ValueError:
                    pass

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def extract_deadline_from_title(self, title: str) -> Optional[date]:
        """Extract deadline date from title text

        Handles patterns like:
        - 【1月23日締切】
        - 【2月12日締切】
        - （締切：1月31日）
        - 締切日：令和7年1月20日
        """
        import re
        today = date.today()
        current_year = today.year

        # Pattern: 【X月Y日締切】 or 【X月Y日申請締切】
        match = re.search(r'[【\[（(](\d{1,2})月(\d{1,2})日[^】\]）)]*締切[】\]）)]', title)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            # Determine year: if the month is less than current month, assume next year
            year = current_year
            try:
                deadline = date(year, month, day)
                if deadline < today:
                    deadline = date(year + 1, month, day)
                return deadline
            except ValueError:
                pass

        # Pattern: 締切：X月Y日 or 締切日：X月Y日
        match = re.search(r'締切[日]?[：:]\s*(\d{1,2})月(\d{1,2})日', title)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            year = current_year
            try:
                deadline = date(year, month, day)
                if deadline < today:
                    deadline = date(year + 1, month, day)
                return deadline
            except ValueError:
                pass

        # Pattern: 令和X年X月X日まで or 令和X年X月X日締切
        match = re.search(r'令和(\d+)年(\d{1,2})月(\d{1,2})日(?:まで|締切)?', title)
        if match:
            year = int(match.group(1)) + 2018
            month = int(match.group(2))
            day = int(match.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                pass

        return None

    def parse_amount(self, amount_str: str) -> Optional[int]:
        """Parse amount string to integer"""
        if not amount_str:
            return None

        import re
        # Remove non-numeric characters except for 万, 億
        amount_str = amount_str.strip()

        # Handle 万 (10,000) and 億 (100,000,000)
        if "億" in amount_str:
            match = re.search(r'([\d,.]+)\s*億', amount_str)
            if match:
                num = float(match.group(1).replace(",", ""))
                return int(num * 100_000_000)

        if "万" in amount_str:
            match = re.search(r'([\d,.]+)\s*万', amount_str)
            if match:
                num = float(match.group(1).replace(",", ""))
                return int(num * 10_000)

        # Extract numeric value
        match = re.search(r'([\d,]+)', amount_str)
        if match:
            return int(match.group(1).replace(",", ""))

        return None

    def extract_dates_from_text(self, text: str) -> tuple[Optional[date], Optional[date]]:
        """Extract application start and end dates from page text

        Searches for patterns like:
        - 提出期限：令和7年1月31日
        - 募集期限：2025年2月15日
        - 締切日：1月20日
        - 応募期間：1月10日～1月31日
        - 受付期間：令和7年1月15日から令和7年2月10日まで

        Returns:
            Tuple of (application_start, application_end)
        """
        import re
        today = date.today()
        current_year = today.year

        application_start = None
        application_end = None

        # Keywords that indicate deadline/end date
        end_keywords = [
            "提出期限", "募集期限", "応募期限", "申込期限", "受付期限",
            "締切日", "締切", "期限", "まで", "必着"
        ]

        # Keywords that indicate start date
        start_keywords = [
            "募集開始", "受付開始", "公告日", "掲載日", "公開日", "から"
        ]

        # Pattern: 令和X年X月X日
        reiwa_pattern = r'令和\s*[元\d]+\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'

        # Pattern: YYYY年M月D日 or YYYY/M/D
        western_pattern = r'(\d{4})\s*[年/]\s*(\d{1,2})\s*[月/]\s*(\d{1,2})\s*日?'

        # Pattern: M月D日
        short_pattern = r'(\d{1,2})\s*月\s*(\d{1,2})\s*日'

        # Search for end date patterns
        for keyword in end_keywords:
            # Look for keyword followed by date
            pattern = rf'{keyword}[：:\s]*(?:令和\s*(\d+)\s*年\s*)?(\d{{1,2}})\s*月\s*(\d{{1,2}})\s*日'
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if groups[0]:  # Has 令和 year
                    year = int(groups[0]) + 2018
                    month = int(groups[1])
                    day = int(groups[2])
                else:
                    month = int(groups[1])
                    day = int(groups[2])
                    year = current_year
                    # If date is in the past, assume next year
                    try:
                        test_date = date(year, month, day)
                        if test_date < today:
                            year += 1
                    except ValueError:
                        continue

                try:
                    application_end = date(year, month, day)
                    break
                except ValueError:
                    continue

        # If no end date found, try generic date search near keywords
        if not application_end:
            for keyword in end_keywords:
                idx = text.find(keyword)
                if idx != -1:
                    # Search in a window around the keyword
                    window = text[idx:idx+100]

                    # Try 令和 format
                    match = re.search(r'令和\s*(\d+)\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', window)
                    if match:
                        year = int(match.group(1)) + 2018
                        month = int(match.group(2))
                        day = int(match.group(3))
                        try:
                            application_end = date(year, month, day)
                            break
                        except ValueError:
                            continue

                    # Try western format
                    match = re.search(western_pattern, window)
                    if match:
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                        try:
                            application_end = date(year, month, day)
                            break
                        except ValueError:
                            continue

                    # Try short format
                    match = re.search(short_pattern, window)
                    if match:
                        month = int(match.group(1))
                        day = int(match.group(2))
                        year = current_year
                        try:
                            test_date = date(year, month, day)
                            if test_date < today:
                                year += 1
                            application_end = date(year, month, day)
                            break
                        except ValueError:
                            continue

        # Search for start date patterns (similar logic)
        for keyword in start_keywords:
            idx = text.find(keyword)
            if idx != -1:
                window = text[max(0, idx-20):idx+80]

                match = re.search(r'令和\s*(\d+)\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', window)
                if match:
                    year = int(match.group(1)) + 2018
                    month = int(match.group(2))
                    day = int(match.group(3))
                    try:
                        application_start = date(year, month, day)
                        break
                    except ValueError:
                        continue

        return application_start, application_end

    async def fetch_bid_details(self, bid: BidInfo) -> BidInfo:
        """Fetch detailed information from bid's announcement URL

        Args:
            bid: BidInfo object with announcement_url set

        Returns:
            Updated BidInfo with extracted dates
        """
        if not bid.announcement_url:
            return bid

        soup = await self.fetch_page(bid.announcement_url)
        if not soup:
            return bid

        # Get all text from the page
        text = soup.get_text(separator=' ', strip=True)

        # Extract dates
        start_date, end_date = self.extract_dates_from_text(text)

        if end_date and not bid.application_end:
            bid.application_end = end_date

        if start_date and not bid.application_start:
            bid.application_start = start_date

        return bid

    @abstractmethod
    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from the municipality website

        Returns:
            List of BidInfo objects
        """
        pass
