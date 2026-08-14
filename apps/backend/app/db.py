from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from app.settings import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from langchain_postgres import PGEngine

DB_URL = settings.supabase_db_url
DB_POOL_MIN_SIZE = settings.db_pool_min_size
DB_POOL_MAX_SIZE = settings.db_pool_max_size
DB_POOL_TIMEOUT = settings.db_pool_timeout


def _database_url() -> str:
    if not DB_URL:
        raise RuntimeError("SUPABASE_DB_URL must be set")
    if DB_URL.startswith("postgresql+psycopg://"):
        return DB_URL
    if DB_URL.startswith("postgresql://"):
        return f"postgresql+psycopg://{DB_URL.removeprefix('postgresql://')}"
    if DB_URL.startswith("postgres://"):
        return f"postgresql+psycopg://{DB_URL.removeprefix('postgres://')}"
    raise RuntimeError("SUPABASE_DB_URL must use a PostgreSQL URL")


@lru_cache(maxsize=1)
def engine():
    if DB_POOL_MIN_SIZE < 1 or DB_POOL_MAX_SIZE < DB_POOL_MIN_SIZE:
        raise RuntimeError("DB_POOL_MIN_SIZE/MAX_SIZE configuration is invalid")
    db_engine = create_engine(
        _database_url(),
        pool_size=DB_POOL_MAX_SIZE,
        max_overflow=0,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_pre_ping=True,
    )

    return db_engine

def vector_engine() -> PGEngine:
    return PGEngine.from_connection_string(
        _database_url(),
    )

@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def advisory_lock() -> Iterator[None]:
    """Serialize indexing and reindexing processes through PostgreSQL."""
    lock_engine = create_engine(_database_url(), poolclass=NullPool)
    connection = lock_engine.connect()
    locked = False
    try:
        connection.execute(text("SELECT pg_advisory_lock(hashtext('rag.embedding_index'))"))
        locked = True
        yield
    finally:
        if locked:
            connection.execute(
                text("SELECT pg_advisory_unlock(hashtext('rag.embedding_index'))")
            )
        connection.close()
        lock_engine.dispose()


def close_engine() -> None:
    if engine.cache_info().currsize:
        engine().dispose()
        session_factory.cache_clear()
        engine.cache_clear()
