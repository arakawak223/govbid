import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class MiyazakiScraper(BaseScraper):
    """Scraper for Miyazaki Prefecture (宮崎県)"""

    municipality_name = "宮崎県"
    base_url = "https://www.pref.miyazaki.lg.jp"
    bid_list_url = "https://www.pref.miyazaki.lg.jp/kense/chotatsu/nyusatsu/index.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Miyazaki Prefecture website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        # Find the main content
        content = soup.find("div", {"id": "contentsArea"}) or soup

        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託"]):
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                bid = BidInfo(
                    title=text,
                    municipality=self.municipality_name,
                    announcement_url=full_url,
                    source_url=self.bid_list_url,
                )

                # Fetch detailed page to get accurate dates
                bid = await self.fetch_bid_details(bid)

                bids.append(bid)

        return bids
