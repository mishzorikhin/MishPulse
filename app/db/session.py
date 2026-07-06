"""Фабрика сессий SQLAlchemy."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Выдать сессию БД на время обработки запроса."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
