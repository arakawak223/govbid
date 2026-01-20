import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.api.routes import router as api_router
from app.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting GovBid API...")
    await init_db()
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down GovBid API...")
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    description="九州・山口自治体の入札・公募情報を収集・一覧表示するAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境用: すべてのオリジンを許可
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター登録
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy"}
