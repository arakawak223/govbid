import logging
from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class TagawaScraper(BaseScraper):
    """Scraper for Tagawa City (田川市)"""

    municipality_name = "田川市"
    base_url = "https://www.joho.tagawa.fukuoka.jp"
    bid_list_url = "https://www.joho.tagawa.fukuoka.jp/list00609.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Tagawa City website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return await self.enrich_bids_parallel(bids)

        content = soup.find("div", {"class": "contents"}) or soup.find("main") or soup

        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託", "提案"]):
                if any(ex in text for ex in [
                    "質問への回答", "質問に対する回答", "質問回答", "質問と回答",
                    "審査結果", "選定結果", "結果について", "の結果", "決定について"
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
