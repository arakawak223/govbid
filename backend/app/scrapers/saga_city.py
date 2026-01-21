import logging

from app.scrapers.base import BaseScraper, BidInfo

logger = logging.getLogger(__name__)


class SagaCityScraper(BaseScraper):
    """Scraper for Saga City (佐賀市)"""

    municipality_name = "佐賀市"
    base_url = "https://www.city.saga.lg.jp"
    bid_list_url = "https://www.city.saga.lg.jp/main/597.html"

    async def scrape(self) -> list[BidInfo]:
        """Scrape bid information from Saga City website"""
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
                if any(exclude in text for exclude in ["イベント", "参加者", "セミナー", "講座", "ボランティア"]):
                    continue

                if href.startswith("http"):
                    full_url = href
                elif href.startswith("./"):
                    full_url = f"{self.base_url}/{href[2:]}"
                elif href.startswith("/"):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = f"{self.base_url}/{href}"

                bid = BidInfo(
                    title=text,
                    municipality=self.municipality_name,
                    announcement_url=full_url,
                    source_url=self.bid_list_url,
                )

                bids.append(bid)

        return bids
