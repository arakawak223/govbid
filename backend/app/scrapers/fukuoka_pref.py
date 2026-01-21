import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class FukuokaPrefScraper(BaseScraper):
    """Scraper for Fukuoka Prefecture (福岡県)"""

    municipality_name = "福岡県"
    base_url = "https://www.pref.fukuoka.lg.jp"
    bid_list_url = "https://www.pref.fukuoka.lg.jp/bid/"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Fukuoka Prefecture website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        # Find bid listings - they're typically in a list or table
        # Look for links containing bid-related keywords
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Skip navigation and non-bid links
            if not text or len(text) < 10:
                continue

            # Check if this looks like a bid announcement
            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託"]):
                if href.startswith("http"):
                    full_url = href
                elif href.startswith("/"):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = f"{self.base_url}/{href}"

                bid = BidInfo(
                    title=text,
                    municipality=self.municipality_name,
                    announcement_url=full_url,
                    source_url=self.bid_list_url,
                )

                # Try to get more details from the detail page
                detail_soup = await self.fetch_page(full_url)
                if detail_soup:
                    self._parse_detail_page(bid, detail_soup)

                bids.append(bid)

        return bids

    def _parse_detail_page(self, bid: BidInfo, soup: BeautifulSoup) -> None:
        """Parse additional information from the detail page"""
        # Look for deadline/application period
        text = soup.get_text()

        # Look for date patterns
        import re

        # Application deadline
        deadline_match = re.search(
            r'(?:提出期限|申込期限|締切|応募期限)[：:]\s*(.+?)(?:\n|$)',
            text
        )
        if deadline_match:
            bid.application_end = self.parse_date(deadline_match.group(1))

        # Application start
        start_match = re.search(
            r'(?:公告日|募集開始|公募開始)[：:]\s*(.+?)(?:\n|$)',
            text
        )
        if start_match:
            bid.application_start = self.parse_date(start_match.group(1))

        # Contract period
        period_match = re.search(
            r'(?:履行期間|契約期間|業務期間)[：:]\s*(.+?)(?:から|～|~)\s*(.+?)(?:\n|$)',
            text
        )
        if period_match:
            bid.period_start = self.parse_date(period_match.group(1))
            bid.period_end = self.parse_date(period_match.group(2))

        # Amount
        amount_match = re.search(
            r'(?:上限額|予定価格|委託料)[：:]\s*([\d,万億円]+)',
            text
        )
        if amount_match:
            bid.max_amount = self.parse_amount(amount_match.group(1))
