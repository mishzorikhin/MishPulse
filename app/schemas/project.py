"""Pydantic-схемы для запросов и ответов, связанных с проектами."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import ProjectHealth, StatusLevel


class ProjectNotificationsSchema(BaseModel):
    """Настройки уведомлений проекта через ntfy и Telegram."""

    ntfy_server: str | None = Field(
        default=None,
        max_length=500,
        description="Базовый URL ntfy-сервера",
    )
    ntfy_topic: str | None = Field(
        default=None,
        max_length=200,
        description="Топик ntfy для алертов",
    )
    telegram_bot_token: str | None = Field(
        default=None,
        max_length=200,
        description="Токен Telegram-бота",
    )
    telegram_chat_id: str | None = Field(
        default=None,
        max_length=100,
        description="Chat ID для уведомлений",
    )


class ProjectCreateRequest(BaseModel):
    """Запрос на создание проекта."""

    name: str = Field(..., min_length=1, max_length=200, description="Название проекта")
    notifications: ProjectNotificationsSchema | None = Field(
        default=None,
        description="Настройки ntfy/Telegram для алертов о проблемах",
    )


class ProjectResponse(BaseModel):
    """Ответ с информацией о созданном проекте."""

    id: UUID = Field(..., description="Уникальный идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    link: str = Field(..., description="Уникальная ссылка для отправки статусов")
    notifications: ProjectNotificationsSchema = Field(
        ..., description="Настроенные каналы уведомлений"
    )


class ProjectStateResponse(BaseModel):
    """Текущее состояние проекта для сводки/дашборда."""

    id: UUID = Field(..., description="Уникальный идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    token: str = Field(..., description="Токен проекта для heartbeat и управления")
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
