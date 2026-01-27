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
        seen_urls = set()

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            logger.error(f"Failed to fetch page: {self.bid_list_url}")
            return await self.enrich_bids_parallel(bids)

        # Find all links in the entire document (no content filtering)
        # The page uses wb-contents class, not "contents"
        links = soup.find_all("a", href=True)
        logger.info(f"福岡市: Found {len(links)} total links on page")

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            # Skip navigation links, javascript links, etc.
            if href.startswith("#") or href.startswith("javascript:"):
                continue

            # Filter for bid-related content - expanded keywords
            bid_keywords = ["公募", "募集", "企画", "プロポーザル", "委託", "提案", "競技"]
            if any(keyword in text for keyword in bid_keywords):
                # 除外パターン（質問回答、結果ページ）
                exclude_patterns = [
                    "質問への回答", "質問に対する回答", "質問回答", "質問と回答", "質問・回答", "質問及び回答",
                    "に関する質問と回答",  # New: Q&A about specific items
                    "審査結果", "選定結果", "結果について", "の結果", "決定について", "を決定しました", "決定しました",
                    "意見募集", "パブリックコメント",
                    "評価項目", "選定基準",  # Evaluation criteria, not bids
                ]
                if any(ex in text for ex in exclude_patterns):
                    continue

                full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                # Skip duplicate URLs
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                bid = BidInfo(
                    title=text,
                    municipality=self.municipality_name,
                    announcement_url=full_url,
                    source_url=self.bid_list_url,
                )
                bids.append(bid)
                logger.debug(f"福岡市: Found bid: {text[:50]}...")

        logger.info(f"福岡市: Extracted {len(bids)} potential bids before enrichment")
        return await self.enrich_bids_parallel(bids)
