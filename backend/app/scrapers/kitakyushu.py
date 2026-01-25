import logging
from typing import Optional

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class KitakyushuScraper(BaseScraper):
    """Scraper for Kitakyushu City (北九州市)"""

    municipality_name = "北九州市"
    base_url = "https://www.city.kitakyushu.lg.jp"
    bid_list_url = "https://www.city.kitakyushu.lg.jp/business/menu03_00174.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Kitakyushu City website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        # Find tables containing bid information
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue

                # Look for links in the first cell (usually the title)
                link = cells[0].find("a", href=True)
                if not link:
                    continue

                text = link.get_text(strip=True)
                href = link.get("href", "")

                if not text or len(text) < 5:
                    continue

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

                # Try to extract deadline from table cells
                for cell in cells[1:]:
                    cell_text = cell.get_text(strip=True)
                    if "締切" in cell_text or "期限" in cell_text or "/" in cell_text:
                        bid.application_end = self.parse_date(cell_text)
                        break

                if await self.enrich_bid_from_detail(bid):
                    bids.append(bid)

        # Also check for list-based layouts
        lists = soup.find_all("ul", {"class": ["list", "link-list"]})
        for ul in lists:
            for li in ul.find_all("li"):
                link = li.find("a", href=True)
                if link:
                    text = link.get_text(strip=True)
                    href = link.get("href", "")
                    if text and len(text) >= 5:
                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                        bid = BidInfo(
                            title=text,
                            municipality=self.municipality_name,
                            announcement_url=full_url,
                            source_url=self.bid_list_url,
                        )
                        if await self.enrich_bid_from_detail(bid):
                            bids.append(bid)

        return bids
