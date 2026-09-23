"""落札企業抽出のサービス層テスト（クロール〜保存〜重複除去）

ネットワークには出ず、疑似サイト（URL→HTML）を WinnerCrawler._get に差し込んで検証する。

実行: cd backend && python -m pytest tests/test_winner_service.py -v
"""
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base  # noqa: E402
from app.models import Bid, BidResult  # noqa: E402
from app.services import winner_crawler  # noqa: E402
from app.services.winner_service import run_winner_extraction, select_targets  # noqa: E402

DOMAIN = "www.city.test.lg.jp"
KOUBO_URL = f"https://{DOMAIN}/koubo/kanko_douga.html"          # 公募ページ（削除済みを想定）
LIST_URL = f"https://{DOMAIN}/koubo/"                            # 親ディレクトリ
KEKKA_URL = f"https://{DOMAIN}/koubo/kanko_douga_kekka.html"     # 結果ページ

SITE = {
    LIST_URL: """<html><head><title>公募情報</title></head><body>
        <ul>
          <li><a href="kanko_douga_kekka.html">観光プロモーション動画制作業務　選定結果</a></li>
          <li><a href="/soshiki/">組織案内</a></li>
        </ul></body></html>""",
    KEKKA_URL: """<html><head><title>令和6年度 観光プロモーション動画制作業務　選定結果</title></head><body>
        <h1>令和6年度 観光プロモーション動画制作業務　選定結果</h1>
        <p>受託者　（株）テスト映像</p>
        <p>次点者　株式会社ダミー広告</p>
        <p>契約金額　4,500,000円</p>
        </body></html>""",
}


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def fake_site(monkeypatch):
    """疑似サイト。未登録URLは404相当(None)を返す＝公募ページ削除を再現する。"""
    monkeypatch.setattr(winner_crawler.settings, "winner_crawl_delay_seconds", 0)

    async def _get(self, client, url):
        html = SITE.get(url)
        if html is None:
            return None, False
        return html.encode("utf-8"), False

    monkeypatch.setattr(winner_crawler.WinnerCrawler, "_get", _get)


async def _add_bid(db, **kwargs):
    fields = {
        "title": "令和6年度 観光プロモーション動画制作業務",
        "municipality": "テスト市",
        "category": "動画・映像",
        "max_amount": 8_000_000,
        "announcement_url": KOUBO_URL,
        "source_url": LIST_URL,
    }
    fields.update(kwargs)
    bid = Bid(**fields)
    db.add(bid)
    await db.commit()
    await db.refresh(bid)
    return bid


@pytest.mark.asyncio
async def test_対象選定は金額下限と未確認案件で絞る(db):
    await _add_bid(db)
    await _add_bid(db, title="少額案件", max_amount=100_000)

    targets = await select_targets(db, min_amount=5_000_000)
    assert [t.max_amount for t in targets] == [8_000_000]


@pytest.mark.asyncio
async def test_公募ページが消えていても結果ページから抽出して保存する(db, fake_site):
    bid = await _add_bid(db)

    stats = await run_winner_extraction(db, min_amount=5_000_000)

    assert stats["targets"] == 1
    assert stats["extracted"] == 1
    assert stats["saved"] == 1

    saved = (await db.execute(BidResult.__table__.select())).mappings().all()
    assert len(saved) == 1
    row = saved[0]
    assert row["winning_company"] == "株式会社テスト映像"   # 略記を正規化
    assert row["winner_label"] == "受託者"
    assert row["result_url"] == KEKKA_URL                   # 公募URLではなく結果ページ
    assert row["announcement_url"] == KOUBO_URL
    assert row["bid_id"] == bid.id and row["match_method"] == "bid"
    assert row["award_amount"] == 4_500_000
    assert row["extract_source"] == "crawl:heading"


@pytest.mark.asyncio
async def test_再実行しても重複保存しない(db, fake_site):
    await _add_bid(db)

    first = await run_winner_extraction(db, min_amount=5_000_000)
    assert first["saved"] == 1

    # 既に落札企業が判明した案件は次回の対象から外れる
    assert await select_targets(db, min_amount=5_000_000) == []

    # 同じ案件を強制的に再抽出しても、案件core＋企業名で重複除去される
    second = await run_winner_extraction(db, min_amount=5_000_000, limit=None)
    assert second["saved"] == 0

    total = (await db.execute(BidResult.__table__.select())).mappings().all()
    assert len(total) == 1
