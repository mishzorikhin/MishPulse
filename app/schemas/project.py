"""Pydantic-схемы для запросов и ответов, связанных с проектами."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Запрос на создание проекта."""

    name: str = Field(..., description="Название проекта")


class ProjectResponse(BaseModel):
    """Ответ с информацией о созданном проекте."""

    id: UUID = Field(..., description="Уникальный идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    link: str = Field(..., description="Уникальная ссылка для отправки статусов")


class StatusCreateRequest(BaseModel):
    """Запрос на отправку статуса проектом."""

    message: str = Field(..., description="Текст статуса")
    timestamp: datetime | None = Field(
        default=None,
        description="Момент времени формирования статуса. Если не задан, используется текущее время.",
    )


class StatusResponse(BaseModel):
    """Ответ после сохранения статуса."""

    message: str = Field(..., description="Текст статуса")
    timestamp: datetime = Field(..., description="Зафиксированное время статуса")
