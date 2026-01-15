import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Date
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
