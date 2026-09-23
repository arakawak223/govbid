from datetime import datetime, date
from pydantic import BaseModel, EmailStr


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    notification_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str | None = None


# Bid schemas
class BidBase(BaseModel):
    title: str
    municipality: str
    category: str | None = None
    max_amount: int | None = None
    announcement_url: str
    period_start: date | None = None
    period_end: date | None = None
    application_start: date | None = None
    application_end: date | None = None
    status: str = "募集中"
    source_url: str


class BidCreate(BidBase):
    pass


class BidResponse(BidBase):
    id: str
    bid_number: int | None = None
    scraped_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BidListResponse(BaseModel):
    items: list[BidResponse]
    total: int
    page: int
    per_page: int
    pages: int


# Filter schema
class BidFilter(BaseModel):
    municipality: str | None = None
    category: str | None = None
    status: str | None = None
    search: str | None = None
    min_amount: int | None = None
    max_amount: int | None = None


# Notification settings
class NotificationSettings(BaseModel):
    notification_enabled: bool


# 落札企業抽出 schemas
class BidResultResponse(BaseModel):
    id: str
    bid_id: str | None = None
    municipality: str
    title: str
    category: str | None = None
    max_amount: int | None = None
    winning_company: str
    winner_label: str | None = None
    award_amount: int | None = None
    award_date: date | None = None
    announcement_url: str | None = None
    result_url: str
    evidence: str | None = None
    extract_source: str
    match_method: str
    is_verified: bool
    scraped_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BidResultListResponse(BaseModel):
    items: list[BidResultResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CompanyRanking(BaseModel):
    company: str
    count: int


class WinnerExtractRequest(BaseModel):
    """落札企業抽出の実行条件（未指定時は運用既定値）"""
    municipality: str | None = None
    min_amount: int | None = None
    since_days: int | None = None
    limit: int | None = None
    max_pages_per_domain: int | None = None


class WinnerExtractTargets(BaseModel):
    targets: int
    min_amount: int
    municipality: str | None = None
    since_days: int | None = None
