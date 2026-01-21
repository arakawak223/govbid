import logging

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class KagoshimaCityScraper(BaseScraper):
    """Scraper for Kagoshima City (鹿児島市)"""

    municipality_name = "鹿児島市"
    base_url = "https://www.city.kagoshima.lg.jp"
    bid_list_url = "https://www.city.kagoshima.lg.jp/shise/nyusatsu/nyusatsu/itakusonota.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Kagoshima City website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        content = soup.find("div", {"id": "main-contents"}) or soup.find("main") or soup

        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託", "提案", "企画提案"]):
                if any(exclude in text for exclude in ["売却", "電気の購入", "選定結果"]):
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
