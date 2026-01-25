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
                # 除外パターン（質問回答、結果ページ）
                if any(ex in text for ex in [
                    "質問への回答", "質問に対する回答", "質問回答", "質問と回答", "質問・回答", "質問及び回答",
                    "審査結果", "選定結果", "結果について", "の結果", "決定について", "を決定しました", "決定しました",
                    "意見募集", "パブリックコメント"
                ]):
                    continue
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

                # Try to get more details from the detail page (with update date filter)
                if await self.enrich_bid_from_detail(bid):
                    bids.append(bid)

        return bids
