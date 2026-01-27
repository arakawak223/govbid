from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

# Build database URL with prepare_threshold=0 for pgbouncer compatibility
db_url = settings.database_url
if "?" in db_url:
    db_url = f"{db_url}&prepare_threshold=0"
else:
    db_url = f"{db_url}?prepare_threshold=0"

# Use NullPool for Supabase/pgbouncer compatibility
engine = create_async_engine(
    db_url,
    echo=settings.debug,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Migrate: Add bid_number column and assign numbers to existing bids
    await migrate_bid_numbers()


async def migrate_bid_numbers():
    """既存のbidsにbid_numberを付与するマイグレーション"""
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Check if column exists (PostgreSQL)
        try:
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'bids' AND column_name = 'bid_number'"
            ))
            column_exists = result.fetchone() is not None

            if not column_exists:
                # Add the column
                await conn.execute(text(
                    "ALTER TABLE bids ADD COLUMN bid_number INTEGER UNIQUE"
                ))
        except Exception:
            # Column might already exist or different DB, continue
            pass

        # Assign bid_numbers to records that don't have one
        try:
            # Get max bid_number
            result = await conn.execute(text(
                "SELECT COALESCE(MAX(bid_number), 0) FROM bids"
            ))
            max_number = result.scalar() or 0

            # Get bids without bid_number, ordered by created_at
            result = await conn.execute(text(
                "SELECT id FROM bids WHERE bid_number IS NULL ORDER BY created_at ASC"
            ))
            rows = result.fetchall()

            # Assign numbers
            for i, row in enumerate(rows, start=max_number + 1):
                await conn.execute(text(
                    "UPDATE bids SET bid_number = :num WHERE id = :id"
                ), {"num": i, "id": row[0]})
        except Exception as e:
            print(f"Migration warning: {e}")
