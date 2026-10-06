import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings

# asyncpg is not compatible with Windows' default ProactorEventLoop — its
# overlapped-I/O socket transport can drop `_proactor` mid-write, surfacing
# as `AttributeError: 'NoneType' object has no attribute 'send'` under load
# (e.g. across pytest's per-test event loops). SelectorEventLoop doesn't
# have this issue. No async subprocess usage anywhere in this app, so the
# one thing SelectorEventLoop can't do on Windows (subprocess pipes) is moot.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_is_sqlite = "sqlite" in settings.DATABASE_URL
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Postgres/asyncpg connections are bound to the event loop they were
    # opened on. FastAPI's TestClient (and anything else using anyio's
    # from_thread.BlockingPortal) runs the ASGI app on its own background
    # thread with its own loop, separate from whichever loop first opened a
    # pooled connection — reusing that pooled connection from a different
    # loop raises "attached to a different loop" / proactor errors. NullPool
    # avoids caching connections across checkouts entirely, so each checkout
    # is safe regardless of which loop is asking. Not needed for sqlite.
    poolclass=None if _is_sqlite else NullPool,
)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Columns added to tables that already exist in deployed databases.
# create_all() only creates missing TABLES, never missing columns, so each
# later addition is listed here and added in place if absent.
_ADDED_COLUMNS = {
    "projects": {"period": "VARCHAR"},
    "characters": {"wardrobe": "TEXT"},
    "shots": {"board_caption": "TEXT", "board_dialogue": "TEXT", "board_crop": "TEXT"},
}


def _add_missing_columns(sync_conn):
    from sqlalchemy import inspect, text
    inspector = inspect(sync_conn)
    for table, columns in _ADDED_COLUMNS.items():
        if not inspector.has_table(table):
            continue
        present = {c["name"] for c in inspector.get_columns(table)}
        for name, sql_type in columns.items():
            if name not in present:
                sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


async def init_db():
    from app import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
