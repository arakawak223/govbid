import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class OitaScraper(BaseScraper):
    """Scraper for Oita Prefecture (大分県)"""

    municipality_name = "大分県"
    base_url = "https://www.pref.oita.jp"
    bid_list_url = "https://www.pref.oita.jp/site/nyusatu-koubo/list22380-29038.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Oita Prefecture website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        # Find the article list
        content = soup.find("div", {"class": "article-list"}) or soup

        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            full_url = href if href.startswith("http") else f"{self.base_url}{href}"

            bid = BidInfo(
                title=text,
                municipality=self.municipality_name,
                announcement_url=full_url,
                source_url=self.bid_list_url,
            )
            bids.append(bid)

        return bids
