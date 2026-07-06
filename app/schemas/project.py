"""Pydantic-схемы для запросов и ответов, связанных с проектами."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import ProjectHealth, StatusLevel


class ProjectCreateRequest(BaseModel):
    """Запрос на создание проекта."""

    name: str = Field(..., min_length=1, max_length=200, description="Название проекта")


class ProjectResponse(BaseModel):
    """Ответ с информацией о созданном проекте."""

    id: UUID = Field(..., description="Уникальный идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    link: str = Field(..., description="Уникальная ссылка для отправки статусов")


class ProjectStateResponse(BaseModel):
    """Текущее состояние проекта для сводки/дашборда."""

    id: UUID = Field(..., description="Уникальный идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    health: ProjectHealth = Field(..., description="Текущее состояние проекта")
    last_seen: datetime = Field(..., description="Время последнего пульса")
    last_message: str | None = Field(
        default=None, description="Текст последнего полученного статуса"
    )


class StatusCreateRequest(BaseModel):
    """Запрос на отправку статуса проектом."""

    level: StatusLevel = Field(
        default=StatusLevel.OK, description="Уровень статуса: ok, warning или error"
    )
    message: str = Field(default="", max_length=2000, description="Текст статуса")
    timestamp: datetime | None = Field(
        default=None,
        description="Момент времени формирования статуса. Если не задан, используется текущее время.",
    )


class StatusResponse(BaseModel):
    """Ответ после сохранения статуса."""

    level: StatusLevel = Field(..., description="Уровень статуса")
    message: str = Field(..., description="Текст статуса")
    timestamp: datetime = Field(..., description="Зафиксированное время статуса")
