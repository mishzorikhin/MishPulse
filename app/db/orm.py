"""SQLAlchemy ORM-модели для MishPulse."""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ProjectORM(Base):
    """Таблица отслеживаемых проектов."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    health: Mapped[str] = mapped_column(String(20), nullable=False, default="alive")
    last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ntfy_server: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ntfy_topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telegram_bot_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    statuses: Mapped[List["StatusORM"]] = relationship(
        back_populates="project",
        order_by="StatusORM.timestamp",
        cascade="all, delete-orphan",
    )


class StatusORM(Base):
    """Таблица истории статусов проекта."""

    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    project: Mapped[ProjectORM] = relationship(back_populates="statuses")
