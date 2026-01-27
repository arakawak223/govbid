import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class KumamotoCityScraper(BaseScraper):
    """Scraper for Kumamoto City (熊本市)"""

    municipality_name = "熊本市"
    base_url = "https://www.city.kumamoto.jp"
    bid_list_url = "https://www.city.kumamoto.jp/list04401.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Kumamoto City website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return await self.enrich_bids_parallel(bids)

        # Find the content area
        content = soup.find("div", {"id": "contentsArea"}) or soup

        # Look for links in lists or tables
        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            # Skip category links
            if "list" in href.lower() and not any(k in text for k in ["公募", "入札", "プロポーザル"]):
                continue

            # 除外パターン
            exclude_patterns = [
                "ホームページ", "ホームページについて", "公共工事", "工事入札",
                "入札・契約（工事", "広告を募集", "イベント・講座・募集",
                "質問への回答", "質問に対する回答", "質問回答", "質問書への回答", "質問と回答", "質問・回答", "質問及び回答",
                "審査結果", "選定結果", "結果について", "の結果", "決定について", "を決定しました", "決定しました",
                "意見募集", "パブリックコメント"
            ]
            if any(pattern in text for pattern in exclude_patterns):
                continue

            full_url = href if href.startswith("http") else f"{self.base_url}{href}"

            bid = BidInfo(
                title=text,
                municipality=self.municipality_name,
                announcement_url=full_url,
                source_url=self.bid_list_url,
            )
            bids.append(bid)  # Will be enriched in parallel

        return await self.enrich_bids_parallel(bids)
