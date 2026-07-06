"""Базовый класс ORM-моделей."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Общий базовый класс для SQLAlchemy-моделей."""
