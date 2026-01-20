import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class YamaguchiScraper(BaseScraper):
    """Scraper for Yamaguchi Prefecture (山口県)"""

    municipality_name = "山口県"
    base_url = "https://www.pref.yamaguchi.lg.jp"
    bid_list_url = "https://www.pref.yamaguchi.lg.jp/life/6/13/34/"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Yamaguchi Prefecture website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        # Find content area
        content = soup.find("div", {"id": "contentBody"}) or soup

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

                # Fetch detailed page to get accurate dates
                bid = await self.fetch_bid_details(bid)

                bids.append(bid)

        return bids
