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

    def _parse_flexible_date(self, date_str: str) -> Optional[date]:
        """Parse date string that may or may not include year"""
        import re

        if not date_str:
            return None

        date_str = date_str.strip()

        # Convert full-width numbers to half-width
        full_to_half = str.maketrans('０１２３４５６７８９', '0123456789')
        date_str = date_str.translate(full_to_half)

        # Try parsing with year first (令和 or western year)
        parsed = self.parse_date(date_str)
        if parsed:
            return parsed

        # If no year, try to parse month/day and infer year
        match = re.match(r'(\d{1,2})月(\d{1,2})日', date_str)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            today = date.today()

            # Determine year based on context:
            # - For deadlines, if the month is far in the future (>2 months ahead),
            #   it's likely from the previous year
            # - If the month is less than current month, assume next year (for future dates)
            # - Otherwise, assume current year
            year = today.year

            # Calculate month difference (positive = future, negative = past)
            month_diff = month - today.month

            if month_diff > 2:
                # Month is significantly ahead (e.g., December when we're in January)
                # This is likely a date from the previous year
                year = today.year - 1
            elif month_diff < 0 or (month_diff == 0 and day < today.day):
                # Month is behind current month, or same month but day has passed
                # For deadlines, this means it's already passed this year
                # Keep current year (the deadline has passed)
                pass

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

    async def fetch_detail_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a detail page and return BeautifulSoup object (with logging)"""
        logger.debug(f"Fetching detail page: {url}")
        soup = await self.fetch_page(url)
        if soup:
            logger.debug(f"Successfully fetched detail page: {url}")
        return soup

    def _parse_detail_page(self, bid: BidInfo, soup: BeautifulSoup) -> None:
        """Parse additional information from a detail page using common Japanese patterns"""
        import re
        text = soup.get_text()

        # Convert full-width to half-width for easier parsing
        full_to_half = str.maketrans('０１２３４５６７８９，：', '0123456789,:')
        normalized_text = text.translate(full_to_half)

        # Application deadline: 提出期限、申込期限、締切、応募期限、提案書提出期限、参加意向申出書、参加表明書
        if not bid.application_end:
            # First, try to find date ranges and extract the end date
            # Pattern: 令和X年Y月Z日～令和A年B月C日 or Y月Z日から B月C日まで
            date_range_patterns = [
                # 令和X年Y月Z日（曜日）～令和A年B月C日（曜日）
                r'(令和\d+年\d{1,2}月\d{1,2}日)[（\(][^）\)]*[）\)]\s*(?:～|~|から|－|ー|−|〜)\s*(令和\d+年\d{1,2}月\d{1,2}日)',
                # 令和X年Y月Z日～令和A年B月C日
                r'(令和\d+年\d{1,2}月\d{1,2}日)\s*(?:～|~|から|－|ー|−|〜)\s*(令和\d+年\d{1,2}月\d{1,2}日)',
                # Y月Z日（曜日）からB月C日（曜日）まで
                r'(\d{1,2}月\d{1,2}日)[（\(][^）\)]*[）\)]\s*(?:から|～|~)\s*(\d{1,2}月\d{1,2}日|\d{1,2}日)',
                # Y月Z日からB月C日まで
                r'(\d{1,2}月\d{1,2}日)\s*(?:から|～|~)\s*(\d{1,2}月\d{1,2}日|\d{1,2}日)',
            ]

            # Look for date ranges near keywords
            keywords_for_deadline = [
                '参加表明書', '参加申出書', '参加意向申出書', '提出期間', '受付期間',
                '申込期限', '応募期限', '提出期限', '受付期限'
            ]

            for keyword in keywords_for_deadline:
                if keyword in normalized_text:
                    # Find the keyword position and look for dates nearby
                    keyword_pos = normalized_text.find(keyword)
                    # Look at text within 200 chars after the keyword
                    search_text = normalized_text[keyword_pos:keyword_pos + 300]

                    for pattern in date_range_patterns:
                        match = re.search(pattern, search_text)
                        if match:
                            # Get the end date (second group)
                            end_date_str = match.group(2)
                            # If it's just a day number like "30日", we need to get month from first date
                            if re.match(r'^\d{1,2}日$', end_date_str):
                                start_date_str = match.group(1)
                                month_match = re.search(r'(\d{1,2})月', start_date_str)
                                if month_match:
                                    end_date_str = f"{month_match.group(1)}月{end_date_str}"

                            parsed = self._parse_flexible_date(end_date_str)
                            if parsed:
                                bid.application_end = parsed
                                break
                    if bid.application_end:
                        break

            # Fallback to original patterns if no date found
            if not bid.application_end:
                deadline_patterns = [
                    r'(?:参加意向申出書提出期限|参加表明書の受付期間|参加表明書などの提出期間|参加申出書の受付|参加申込書提出期限|提案書類?提出期限|書類提出期限|提出期限|提出期間|申込期限|応募期限|申請期限|受付期限|締切日?)[：:は]?\s*[　\s]*(.+?)(?:\n|$)',
                ]
                for pattern in deadline_patterns:
                    match = re.search(pattern, normalized_text)
                    if match:
                        parsed = self.parse_date(match.group(1))
                        if parsed:
                            bid.application_end = parsed
                            break

        # Application start: 公告日、募集開始、公募開始、公示日
        if not bid.application_start:
            start_patterns = [
                r'(?:公告日|募集開始日?|公募開始日?|公示日|掲載日|掲示日)[：:は]?\s*[　\s]*(.+?)(?:\n|$)',
                r'(?:公告|公示|公募)\s*(?:日|開始)[：:は]?\s*[　\s]*(.+?)(?:\n|$)',
            ]
            for pattern in start_patterns:
                match = re.search(pattern, normalized_text)
                if match:
                    parsed = self.parse_date(match.group(1))
                    if parsed:
                        bid.application_start = parsed
                        break

        # Contract/implementation period: 履行期間、契約期間、業務期間、実施期間、委託期間、業務委託期間
        if not bid.period_start or not bid.period_end:
            period_patterns = [
                r'(?:履行期間|契約期間|業務期間|実施期間|委託期間|事業期間|業務委託期間)[：:は]?\s*[　\s]*(.+?)(?:から|～|~|－|ー|−|〜)\s*(.+?)(?:\n|$|まで)',
                r'(?:履行期間|契約期間|業務期間|実施期間|委託期間|事業期間|業務委託期間)[：:は]?\s*[　\s]*(.+?)(?:\n|$)',
            ]
            for pattern in period_patterns:
                match = re.search(pattern, normalized_text)
                if match:
                    if match.lastindex >= 2:
                        # Pattern with start and end
                        start_parsed = self.parse_date(match.group(1))
                        end_parsed = self.parse_date(match.group(2))
                        if start_parsed:
                            bid.period_start = start_parsed
                        if end_parsed:
                            bid.period_end = end_parsed
                        break
                    elif match.lastindex >= 1:
                        # Try to find dates within the matched text
                        period_text = match.group(1)
                        dates = re.findall(r'(\d{4}年\d{1,2}月\d{1,2}日|令和\d+年\d{1,2}月\d{1,2}日)', period_text)
                        if len(dates) >= 2:
                            bid.period_start = self.parse_date(dates[0])
                            bid.period_end = self.parse_date(dates[1])
                            break
                        elif len(dates) == 1:
                            bid.period_end = self.parse_date(dates[0])
                            break

        # Amount patterns - expanded to cover more variations
        # 契約限度金額、委託契約の限度額、上限額、予定価格、委託料、予算額、限度額、参考価格、提案限度価格
        if not bid.max_amount:
            amount_patterns = [
                r'(?:提案限度価格|契約限度金額|委託契約の限度額|契約の限度額|限度額|上限額|上限金額|予定価格|委託料|予算額|参考価格|契約上限額?)[：:は]?\s*[　\s]*([\d,]+)\s*円',
                r'([\d,]+)\s*円\s*(?:以内|を上限|が上限|（税込|（消費税)',
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, normalized_text)
                if match:
                    parsed = self.parse_amount(match.group(1) + '円')
                    if parsed:
                        bid.max_amount = parsed
                        break

    def _extract_update_date(self, soup: BeautifulSoup) -> Optional[date]:
        """Extract update date from detail page (更新日)"""
        import re
        text = soup.get_text()

        # Convert full-width to half-width
        full_to_half = str.maketrans('０１２３４５６７８９', '0123456789')
        text = text.translate(full_to_half)

        # Common patterns for update date - expanded
        patterns = [
            # 更新日系
            r'更新日[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'更新日[：:\s]*(\d{4}/\d{1,2}/\d{1,2})',
            r'更新日[：:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'更新日[：:\s]*(令和\d+年\d{1,2}月\d{1,2}日)',
            r'最終更新[日：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'最終更新[日：:\s]*(令和\d+年\d{1,2}月\d{1,2}日)',
            # 掲載日系
            r'掲載日[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'掲載日[：:\s]*(令和\d+年\d{1,2}月\d{1,2}日)',
            r'掲載日[：:\s]*(\d{4}/\d{1,2}/\d{1,2})',
            # 登録日系
            r'登録日[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'登録日[：:\s]*(令和\d+年\d{1,2}月\d{1,2}日)',
            # 公開日系
            r'公開日[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'公開日[：:\s]*(令和\d+年\d{1,2}月\d{1,2}日)',
            # 作成日系
            r'作成日[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'作成日[：:\s]*(令和\d+年\d{1,2}月\d{1,2}日)',
            # ページ更新日
            r'ページ更新日[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'ページ更新日[：:\s]*(令和\d+年\d{1,2}月\d{1,2}日)',
            # 括弧内の日付（よくあるパターン）
            r'\((\d{4}年\d{1,2}月\d{1,2}日)\s*(?:更新|掲載|登録)\)',
            r'（(\d{4}年\d{1,2}月\d{1,2}日)\s*(?:更新|掲載|登録)）',
            r'\((令和\d+年\d{1,2}月\d{1,2}日)\s*(?:更新|掲載|登録)\)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                parsed = self.parse_date(match.group(1))
                if parsed:
                    return parsed
        return None

    def _extract_fiscal_year_from_title(self, title: str) -> Optional[int]:
        """Extract fiscal year from title (令和X年度 or 20XX年度)"""
        import re

        # Convert full-width to half-width
        full_to_half = str.maketrans('０１２３４５６７８９', '0123456789')
        title = title.translate(full_to_half)

        # 令和X年度 pattern
        match = re.search(r'令和\s*(\d+)\s*年度', title)
        if match:
            reiwa_year = int(match.group(1))
            return reiwa_year + 2018  # 令和1年 = 2019年

        # 20XX年度 pattern
        match = re.search(r'(20\d{2})\s*年度', title)
        if match:
            return int(match.group(1))

        # R + number pattern (e.g., R6, R7)
        match = re.search(r'[Rr]\s*(\d+)\s*(?:年度)?', title)
        if match:
            reiwa_year = int(match.group(1))
            return reiwa_year + 2018

        return None

    def _is_too_old(self, update_date: Optional[date], months: int = 1) -> bool:
        """Check if update date is older than specified months"""
        if not update_date:
            return False  # If no date found, don't exclude

        from datetime import timedelta
        cutoff = date.today() - timedelta(days=months * 30)
        return update_date < cutoff

    def _is_deadline_passed(self, application_end: Optional[date]) -> bool:
        """Check if application deadline has already passed"""
        if not application_end:
            return False  # If no deadline found, don't exclude
        return application_end < date.today()

    def _is_old_fiscal_year(self, title: str) -> bool:
        """Check if bid is from an old fiscal year based on title"""
        fiscal_year = self._extract_fiscal_year_from_title(title)
        if not fiscal_year:
            return False  # If can't determine, don't exclude

        # Current fiscal year in Japan (April to March)
        today = date.today()
        if today.month >= 4:
            current_fiscal_year = today.year
        else:
            current_fiscal_year = today.year - 1

        # Allow current and next fiscal year only
        # e.g., in Jan 2026, FY2025 and FY2026 are valid
        return fiscal_year < current_fiscal_year

    def _should_exclude_by_title(self, title: str) -> bool:
        """Check if bid should be excluded based on title keywords.

        Excludes:
        - Photo submissions (写真の募集)
        - Job shadowing/work experience recruitment (職場体験の募集、ジョブシャドウイング)
        - Advertisement space recruitment (広告募集)
        - Q&A documents (質問および回答、質問・回答、Q&A)
        - Recruitment for events that are not service contracts
        """
        exclude_keywords = [
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
            "参加者募集",  # イベント参加者募集
            "出店者募集",
            "出展者募集",
        ]

        for keyword in exclude_keywords:
            if keyword in title:
                logger.debug(f"Excluding by keyword '{keyword}': {title[:50]}")
                return True
        return False

    async def enrich_bid_from_detail(self, bid: BidInfo) -> bool:
        """Fetch detail page and enrich bid information.
        Returns False if bid should be excluded (too old or irrelevant), True otherwise."""

        # Check title-based exclusions first (before fetching detail page)
        if self._should_exclude_by_title(bid.title):
            return False

        # Check fiscal year from title first (before fetching detail page)
        if self._is_old_fiscal_year(bid.title):
            fiscal_year = self._extract_fiscal_year_from_title(bid.title)
            logger.debug(f"Excluding old fiscal year ({fiscal_year}): {bid.title[:40]}")
            return False

        if not bid.announcement_url:
            return True

        soup = await self.fetch_detail_page(bid.announcement_url)
        if soup:
            # Check update date
            update_date = self._extract_update_date(soup)
            if self._is_too_old(update_date, months=2):
                logger.debug(f"Excluding old bid (updated {update_date}): {bid.title[:40]}")
                return False

            self._parse_detail_page(bid, soup)

            # Check if application deadline has passed
            if self._is_deadline_passed(bid.application_end):
                logger.debug(f"Excluding expired bid (deadline {bid.application_end}): {bid.title[:40]}")
                return False

        return True

    async def enrich_bids_parallel(self, bids: list[BidInfo], max_concurrent: int = 3) -> list[BidInfo]:
        """Enrich multiple bids in parallel with concurrency limit.

        Args:
            bids: List of BidInfo objects to enrich
            max_concurrent: Maximum concurrent detail page fetches

        Returns:
            List of enriched BidInfo objects (excluding filtered ones)
        """
        if not bids:
            return []

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_bid(bid: BidInfo) -> Optional[BidInfo]:
            async with semaphore:
                try:
                    should_include = await self.enrich_bid_from_detail(bid)
                    return bid if should_include else None
                except Exception as e:
                    logger.error(f"Error enriching bid {bid.title[:30]}: {e}")
                    return bid  # Include on error

        tasks = [process_bid(bid) for bid in bids]
        results = await asyncio.gather(*tasks)

        # Filter out None values (excluded bids)
        return [bid for bid in results if bid is not None]

    @abstractmethod
    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from the municipality website

        Returns:
            List of BidInfo objects
        """
        pass
