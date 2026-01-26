import logging
from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class ImariScraper(BaseScraper):
    """Scraper for Imari City (伊万里市)"""

    municipality_name = "伊万里市"
    base_url = "https://www.city.imari.lg.jp"
    bid_list_url = "https://www.city.imari.lg.jp/6132.htm"

    async def scrape(self) -> list[BidInfo]:
        bids = []
        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        content = soup.find("div", {"class": "contents"}) or soup.find("main") or soup
        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託", "提案"]):
                if any(ex in text for ex in ["質問への回答", "質問回答", "審査結果", "選定結果", "結果について", "決定について"]):
                    continue
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                bid = BidInfo(title=text, municipality=self.municipality_name, announcement_url=full_url, source_url=self.bid_list_url)
                if await self.enrich_bid_from_detail(bid):
                    bids.append(bid)
        return bids
