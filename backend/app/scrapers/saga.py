import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class SagaScraper(BaseScraper):
    """Scraper for Saga Prefecture (佐賀県)"""

    municipality_name = "佐賀県"
    base_url = "https://www.pref.saga.lg.jp"
    bid_list_urls = [
        "https://www.pref.saga.lg.jp/list00632.html",  # 入札
        "https://www.pref.saga.lg.jp/list02043.html",  # その他委託業務
    ]

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Saga Prefecture website"""
        bids = []

        for list_url in self.bid_list_urls:
            soup = await self.fetch_page(list_url)
            if not soup:
                continue

            # Find content lists
            content = soup.find("div", {"id": "contentsArea"}) or soup

            links = content.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                if not text or len(text) < 10:
                    continue

                # Skip navigation links
                if href.startswith("#") or "list" in href.lower():
                    if not any(k in text for k in ["公募", "募集", "プロポーザル"]):
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
                    source_url=list_url,
                )
                bids.append(bid)

        return bids
