import logging

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class OitaCityScraper(BaseScraper):
    """Scraper for Oita City (大分市)"""

    municipality_name = "大分市"
    base_url = "https://www.city.oita.oita.jp"
    bid_list_url = "https://www.city.oita.oita.jp/shigotosangyo/proposal/proposal/kobogata/index.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Oita City website"""
        bids = []

        soup = await self.fetch_page(self.bid_list_url)
        if not soup:
            return bids

        content = soup.find("div", {"id": "main"}) or soup.find("main") or soup

        links = content.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            if any(keyword in text for keyword in ["公募", "募集", "企画", "プロポーザル", "委託", "提案"]):
                if any(exclude in text for exclude in [
                    "質問について", "質問への回答", "質問に対する回答", "質問回答", "質問と回答", "質問・回答", "質問及び回答",
                    "審査結果", "選定結果", "結果について", "の結果", "決定について", "を決定しました", "決定しました",
                    "意見募集", "パブリックコメント",
                    "ホームページ", "公共工事", "工事入札", "広告を募集"
                ]):
                    continue

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
