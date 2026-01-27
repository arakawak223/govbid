import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class FukuokaCityScraper(BaseScraper):
    """Scraper for Fukuoka City (福岡市)"""

    municipality_name = "福岡市"
    base_url = "https://www.city.fukuoka.lg.jp"
    bid_list_url = "https://www.city.fukuoka.lg.jp/business/keiyaku-kobo/teiankyogi.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Fukuoka City website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return await self.enrich_bids_parallel(bids)

        # Find the main content area
        content = soup.find("div", {"class": "contents"}) or soup.find("main") or soup

        # Find all links that look like bid announcements
        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            # Filter for bid-related content
            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託", "提案"]):
                # 除外パターン（質問回答、結果ページ）
                if any(ex in text for ex in [
                    "質問への回答", "質問に対する回答", "質問回答", "質問と回答", "質問・回答", "質問及び回答",
                    "審査結果", "選定結果", "結果について", "の結果", "決定について", "を決定しました", "決定しました",
                    "意見募集", "パブリックコメント"
                ]):
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
