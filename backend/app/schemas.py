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
