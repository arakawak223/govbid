import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class KagoshimaScraper(BaseScraper):
    """Scraper for Kagoshima Prefecture (鹿児島県)"""

    municipality_name = "鹿児島県"
    base_url = "http://www.pref.kagoshima.jp"
    bid_list_url = "http://www.pref.kagoshima.jp/kensei/nyusatu/nyusatujoho/index.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Kagoshima Prefecture website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        # Find content area
        content = soup.find("div", {"id": "contents"}) or soup

        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託", "入札"]):
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                bid = BidInfo(
                    title=text,
                    municipality=self.municipality_name,
                    announcement_url=full_url,
                    source_url=self.bid_list_url,
                )
                bids.append(bid)

        return bids
