# -*- coding: utf-8 -*-
"""落札企業抽出のオーケストレーション。

対象案件の選定 → 結果ページのクロール → 抽出 → 重複除去 → 保存 までを担う。
選定条件は運用実績の定例条件（調査日が対象期間内・落札企業が未確認・委託料上限が一定以上・URLあり）を既定値とする。
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Bid, BidResult
from app.services.winner_crawler import CaseTarget, WinnerCrawler, WinnerHit
from app.services.winner_extract import company_key, title_core

settings = get_settings()
logger = logging.getLogger(__name__)


async def select_targets(
    db: AsyncSession,
    municipality: Optional[str] = None,
    min_amount: Optional[int] = None,
    since: Optional[date] = None,
    limit: Optional[int] = None,
    include_resolved: bool = False,
) -> list[Bid]:
    """落札企業を探す対象案件を選ぶ。

    既定は「落札企業が未確認・委託料上限が winner_min_amount 以上・公告URLあり」。
    """
    if min_amount is None:
        min_amount = settings.winner_min_amount

    query = select(Bid).where(Bid.announcement_url.isnot(None), Bid.announcement_url != "")
    if municipality:
        query = query.where(Bid.municipality == municipality)
    if min_amount:
        query = query.where(Bid.max_amount >= min_amount)
    if since:
        query = query.where(Bid.scraped_at >= datetime.combine(since, datetime.min.time()))

    if not include_resolved:
        resolved = select(BidResult.bid_id).where(BidResult.bid_id.isnot(None))
        query = query.where(Bid.id.notin_(resolved))

    query = query.order_by(Bid.max_amount.desc().nullslast())
    if limit:
        query = query.limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


def _dedupe_hits(hits: list[WinnerHit], bids: dict[str, Bid]) -> list[WinnerHit]:
    """バッチ内の重複除去。「案件core＋企業名」と「結果URL＋企業名」の両方で判定する。"""
    seen_case: set[tuple[str, str]] = set()
    seen_url: set[tuple[str, str]] = set()
    out: list[WinnerHit] = []
    for h in hits:
        bid = bids.get(h.key)
        ckey = title_core(bid.title) if bid else h.key
        comp = company_key(h.company)
        if (ckey, comp) in seen_case or (h.result_url, comp) in seen_url:
            continue
        seen_case.add((ckey, comp))
        seen_url.add((h.result_url, comp))
        out.append(h)
    return out


async def save_hits(db: AsyncSession, hits: list[WinnerHit], bids: dict[str, Bid]) -> dict:
    """抽出結果を保存する。既存と重複するものはスキップ（更新もしない＝初出を残す）。"""
    saved, duplicated = 0, 0
    for h in _dedupe_hits(hits, bids):
        bid = bids.get(h.key)
        comp = company_key(h.company)
        ckey = title_core(bid.title) if bid else h.key

        existing = await db.execute(
            select(BidResult).where(
                BidResult.company_key == comp,
                (BidResult.case_key == ckey) | (BidResult.result_url == h.result_url),
            )
        )
        if existing.scalars().first():
            duplicated += 1
            continue

        db.add(BidResult(
            bid_id=bid.id if bid else None,
            municipality=bid.municipality if bid else "",
            title=bid.title if bid else "",
            case_key=ckey,
            category=bid.category if bid else None,
            max_amount=bid.max_amount if bid else None,
            winning_company=h.company,
            company_key=comp,
            winner_label=h.label,
            award_amount=h.amount,
            announcement_url=bid.announcement_url if bid else None,
            result_url=h.result_url,
            evidence=h.evidence,
            extract_source=h.source,
            match_method="bid" if bid else "orphan",
            scraped_at=datetime.utcnow(),
        ))
        saved += 1

    await db.commit()
    return {"saved": saved, "duplicated": duplicated}


async def run_winner_extraction(
    db: AsyncSession,
    municipality: Optional[str] = None,
    min_amount: Optional[int] = None,
    since_days: Optional[int] = None,
    limit: Optional[int] = None,
    max_pages_per_domain: Optional[int] = None,
) -> dict:
    """落札企業抽出を実行する。手動トリガーと月次バッチで同じコードパスを通る。"""
    since = date.today() - timedelta(days=since_days) if since_days else None
    bids = await select_targets(db, municipality, min_amount, since, limit)
    logger.info(f"落札企業抽出: 対象 {len(bids)}件")

    if not bids:
        return {
            "targets": 0, "domains": 0, "fetched_pages": 0,
            "extracted": 0, "saved": 0, "duplicated": 0, "errors": [],
        }

    bid_map = {b.id: b for b in bids}
    cases = [
        CaseTarget(key=b.id, title=b.title, url=b.announcement_url, municipality=b.municipality)
        for b in bids
    ]

    crawler = WinnerCrawler(max_pages_per_domain=max_pages_per_domain)
    hits = await crawler.crawl(cases)
    logger.info(f"落札企業抽出: 検出 {len(hits)}件 / 取得 {crawler.stats.fetched}ページ")

    stats = await save_hits(db, hits, bid_map)
    return {
        "targets": len(bids),
        "domains": crawler.stats.domains,
        "fetched_pages": crawler.stats.fetched,
        "extracted": len(hits),
        "saved": stats["saved"],
        "duplicated": stats["duplicated"],
        "errors": crawler.stats.errors[:20],
    }
