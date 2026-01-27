import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class NagasakiScraper(BaseScraper):
    """Scraper for Nagasaki Prefecture (長崎県)"""

    municipality_name = "長崎県"
    base_url = "https://www.pref.nagasaki.jp"
    bid_list_url = "https://www.pref.nagasaki.jp/bunrui/other-bunrui/nyusatsu-other-bunrui/"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Nagasaki Prefecture website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return await self.enrich_bids_parallel(bids)

        # Find bid listings
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            # Look for bid-related content
            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託", "入札"]):
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
