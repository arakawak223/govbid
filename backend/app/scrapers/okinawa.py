import logging
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class OkinawaScraper(BaseScraper):
    """Scraper for Okinawa Prefecture (沖縄県)

    Site structure (3 levels):
      Level 1: /1015342/index.html               - 13 category links
      Level 2: /1015342/{cat_id}/index.html       - fiscal year links (令和5~8年度)
      Level 3: /1015342/{cat_id}/{fy_id}/index.html - individual bid links
    """

    municipality_name = "沖縄県"
    base_url = "https://www.pref.okinawa.lg.jp"
    bid_list_url = "https://www.pref.okinawa.lg.jp/shigoto/nyusatsukeiyaku/1015342/index.html"

    # Keywords that indicate a bid link
    BID_KEYWORDS = ["公募", "募集", "企画", "プロポーザル", "委託"]

    # Exclusion patterns (Q&A, results pages)
    EXCLUDE_PATTERNS = [
        "質問への回答", "質問に対する回答", "質問回答", "質問と回答", "質問・回答", "質問及び回答",
        "審査結果", "選定結果", "結果について", "の結果", "決定について", "を決定しました", "決定しました",
        "意見募集", "パブリックコメント",
    ]

    def _get_current_fiscal_year_reiwa(self) -> list[int]:
        """Return current and next fiscal year as Reiwa era numbers.

        Japanese fiscal year runs April-March.
        Reiwa year = Western year - 2018.
        """
        today = date.today()
        if today.month >= 4:
            current_fy_western = today.year
        else:
            current_fy_western = today.year - 1

        current_reiwa = current_fy_western - 2018
        next_reiwa = current_reiwa + 1
        return [current_reiwa, next_reiwa]

    def _extract_category_links(self, soup: BeautifulSoup) -> list[str]:
        """Extract category page links from the top page (Level 1).

        Category links are under /1015342/ and point to sub-directories.
        """
        content = soup.find("div", {"class": "content"}) or soup
        category_urls = []
        seen = set()

        for link in content.find_all("a", href=True):
            href = link.get("href", "")
            # Category links are like /shigoto/nyusatsukeiyaku/1015342/XXXX/index.html
            # or relative paths like XXXX/index.html
            full_url = urljoin(self.bid_list_url, href)

            # Must be under /1015342/ and be a sub-directory (not the top page itself)
            if "/1015342/" not in full_url:
                continue
            # Extract the path after /1015342/
            match = re.search(r"/1015342/(\d+)/", full_url)
            if not match:
                continue

            if full_url not in seen:
                seen.add(full_url)
                category_urls.append(full_url)
                logger.debug(f"Found category link: {full_url}")

        logger.info(f"Found {len(category_urls)} category pages")
        return category_urls

    def _extract_current_fy_links(self, soup: BeautifulSoup, category_url: str) -> list[str]:
        """Extract current fiscal year page links from a category page (Level 2).

        Only follows links whose text contains '令和X年度' for current/next FY.
        """
        content = soup.find("div", {"class": "content"}) or soup
        fy_urls = []
        target_reiwa_years = self._get_current_fiscal_year_reiwa()

        for link in content.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link.get("href", "")

            # Check if link text matches current or next fiscal year
            for reiwa_year in target_reiwa_years:
                if f"令和{reiwa_year}年度" in text or f"令和{reiwa_year}年" in text:
                    full_url = urljoin(category_url, href)
                    fy_urls.append(full_url)
                    logger.debug(f"Found FY link: {text} -> {full_url}")
                    break

        return fy_urls

    def _extract_bids_from_page(self, soup: BeautifulSoup, source_url: str) -> list[BidInfo]:
        """Extract individual bid links from a fiscal year page (Level 3)."""
        content = soup.find("div", {"class": "content"}) or soup
        bids = []
        seen_urls = set()

        for link in content.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            if not any(keyword in text for keyword in self.BID_KEYWORDS):
                continue

            if any(ex in text for ex in self.EXCLUDE_PATTERNS):
                continue

            full_url = urljoin(source_url, href)

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            bid = BidInfo(
                title=text,
                municipality=self.municipality_name,
                announcement_url=full_url,
                source_url=source_url,
            )
            bids.append(bid)

        return bids

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Okinawa Prefecture website.

        Traverses 3 levels:
          1. Top page -> category links
          2. Category pages -> current fiscal year links
          3. Fiscal year pages -> individual bid links
        """
        bids = []
        seen_urls: set[str] = set()

        # Level 1: Top page -> category links
        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return await self.enrich_bids_parallel(bids)

        category_urls = self._extract_category_links(soup)

        # Level 2: Category pages -> current FY links
        for cat_url in category_urls:
            cat_soup = await self.fetch_page(cat_url)
            if not cat_soup:
                continue

            fy_urls = self._extract_current_fy_links(cat_soup, cat_url)

            # Level 3: FY pages -> individual bid links
            for fy_url in fy_urls:
                fy_soup = await self.fetch_page(fy_url)
                if not fy_soup:
                    continue

                page_bids = self._extract_bids_from_page(fy_soup, fy_url)
                for bid in page_bids:
                    if bid.announcement_url not in seen_urls:
                        seen_urls.add(bid.announcement_url)
                        bids.append(bid)

        logger.info(f"Found {len(bids)} bids across {len(category_urls)} categories")
        return await self.enrich_bids_parallel(bids)
