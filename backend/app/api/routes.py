from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User, Bid
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    BidResponse,
    BidListResponse,
    NotificationSettings,
)
from app.api.deps import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)

settings = get_settings()
router = APIRouter()


# =============================================================================
# Authentication Routes
# =============================================================================

@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """新規ユーザー登録"""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています",
        )

    # Create user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """ログイン"""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """現在のユーザー情報取得"""
    return current_user


@router.put("/auth/notification", response_model=UserResponse)
async def update_notification_settings(
    settings_data: NotificationSettings,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """通知設定の更新"""
    current_user.notification_enabled = settings_data.notification_enabled
    await db.commit()
    await db.refresh(current_user)
    return current_user


# =============================================================================
# Bid Routes
# =============================================================================

@router.get("/bids", response_model=BidListResponse)
async def get_bids(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    municipality: str | None = None,
    category: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    min_amount: int | None = None,
    max_amount: int | None = None,
):
    """入札案件一覧取得"""
    query = select(Bid)

    # Apply filters
    if municipality:
        query = query.where(Bid.municipality == municipality)
    if category:
        query = query.where(Bid.category == category)
    if status_filter:
        query = query.where(Bid.status == status_filter)
    if search:
        query = query.where(Bid.title.ilike(f"%{search}%"))
    if min_amount is not None:
        query = query.where(Bid.max_amount >= min_amount)
    if max_amount is not None:
        query = query.where(Bid.max_amount <= max_amount)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination and ordering
    query = query.order_by(Bid.application_end.desc().nullsfirst(), Bid.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    bids = result.scalars().all()

    return BidListResponse(
        items=bids,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/bids/{bid_id}", response_model=BidResponse)
async def get_bid(
    bid_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """入札案件詳細取得"""
    result = await db.execute(select(Bid).where(Bid.id == bid_id))
    bid = result.scalar_one_or_none()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="案件が見つかりません",
        )
    return bid


@router.get("/municipalities", response_model=list[str])
async def get_municipalities(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """自治体一覧取得"""
    result = await db.execute(
        select(Bid.municipality).distinct().order_by(Bid.municipality)
    )
    return [row[0] for row in result.all()]


@router.get("/categories", response_model=list[str])
async def get_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """カテゴリ一覧取得"""
    result = await db.execute(
        select(Bid.category).distinct().where(Bid.category.isnot(None)).order_by(Bid.category)
    )
    return [row[0] for row in result.all()]


# =============================================================================
# Scrape Routes
# =============================================================================

@router.post("/scrape")
async def run_scrape(
    db: Annotated[AsyncSession, Depends(get_db)],
    municipality: str | None = None,
):
    """手動スクレイピング実行"""
    from app.services.scraper_service import run_all_scrapers, run_single_scraper

    if municipality:
        result = await run_single_scraper(db, municipality)
    else:
        result = await run_all_scrapers(db)

    return result


@router.get("/scrape/municipalities", response_model=list[str])
async def get_supported_municipalities():
    """サポートされている自治体一覧取得"""
    from app.services.scraper_service import get_municipality_names
    return get_municipality_names()
