import os
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def database_url() -> str:
    value = os.getenv("DB_URL")
    if not value:
        pytest.skip("DB_URL is not configured; PostgreSQL integration tests skipped")
    return value


@pytest.fixture()
def db_session_factory(database_url: str) -> Generator[sessionmaker, None, None]:
    normalized_url = database_url
    if normalized_url.startswith("postgresql://"):
        normalized_url = normalized_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif normalized_url.startswith("postgres://"):
        normalized_url = normalized_url.replace("postgres://", "postgresql+psycopg://", 1)
    engine = create_engine(normalized_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            migration = Path(__file__).parents[1].joinpath(
                "migrations/004_chat_history.sql"
            ).read_text()
            connection.exec_driver_sql(migration)
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        yield factory
        with engine.begin() as connection:
            connection.execute(text("truncate chat.messages, chat.conversations cascade"))
    finally:
        engine.dispose()
