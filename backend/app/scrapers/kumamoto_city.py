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
    # Additional pages to scrape (pagination handler returns partial HTML)
    pagination_url_template = "https://www.city.kumamoto.jp/dynamic/hpkiji/pub/hpkijilistpagerhandler.ashx?c_id=3&class_id=4401&class_set_id=1&pg={page}&kbn=alllist"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Kumamoto City website"""
        bids = []
        seen_urls = set()

        # First, scrape the main list page
        soup = await self.fetch_page(self.bid_list_url)
        if soup:
            bids.extend(self._extract_bids_from_soup(soup, seen_urls))

        # Then scrape additional pages (pagination)
        for page in range(1, 6):  # Check pages 1-5
            page_url = self.pagination_url_template.format(page=page)
            soup = await self.fetch_page(page_url)
            if soup:
                new_bids = self._extract_bids_from_soup(soup, seen_urls)
                if not new_bids:
                    break  # No more bids on this page
                bids.extend(new_bids)

        return await self.enrich_bids_parallel(bids)

    def _extract_bids_from_soup(self, soup: BeautifulSoup, seen_urls: set) -> list[BidInfo]:
        """Extract bids from a BeautifulSoup object"""
        bids = []

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

            # Skip if we've already seen this URL
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

        return bids
