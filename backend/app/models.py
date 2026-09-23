import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Date, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    bid_number: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    municipality: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    max_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    announcement_url: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    application_start: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    application_end: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="募集中")
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint on title + municipality + announcement_url to prevent duplicates
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class BidResult(Base):
    """落札企業抽出の結果。

    公募ページは入札後に削除されることが多く、落札情報は別の「結果ページ」に公表される。
    そのため元案件(bids)に紐づかない orphan も保存対象とする（bid_id は nullable）。
    """
    __tablename__ = "bid_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    bid_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)

    # 案件
    municipality: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    case_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # 案件名core（重複除去用）
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    max_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 落札情報
    winning_company: Mapped[str] = mapped_column(String(255), nullable=False)
    company_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # 前株/後株を吸収した名寄せキー
    winner_label: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 「受託者」等、抽出根拠のラベル
    award_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 明示ラベルがある場合のみ
    award_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    # トレース
    announcement_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # 元公告URL
    result_url: Mapped[str] = mapped_column(Text, nullable=False)              # 落札情報を検出したURL
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)          # 抽出箇所の原文
    extract_source: Mapped[str] = mapped_column(String(30), default="crawl")   # crawl:heading/table/block 等
    match_method: Mapped[str] = mapped_column(String(20), default="orphan")    # bid / orphan

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # 人手確認済みフラグ
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 重複除去は「案件core＋企業名」と「結果URL＋企業名」の両方で行う
    # （同一URLの別表記案件が二重計上されるため）
    __table_args__ = (
        Index("ix_bid_results_case_company", "case_key", "company_key"),
        Index("ix_bid_results_url_company", "result_url", "company_key", mysql_length={"result_url": 255}),
    )
