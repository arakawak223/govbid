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
                    source_url=list_url,
                )
                if await self.enrich_bid_from_detail(bid):
                    bids.append(bid)

        return bids
