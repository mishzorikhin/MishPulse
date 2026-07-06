"""Модели данных для проектов и статусов в сервисе MishPulse."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class StatusLevel(str, Enum):
    """Уровень статуса, отправленного клиентом."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class ProjectHealth(str, Enum):
    """Итоговое состояние проекта, вычисляемое сервисом."""

    ALIVE = "alive"
    WARNING = "warning"
    ERROR = "error"
    DEAD = "dead"


class Status(BaseModel):
    """Статус, отправленный проектом."""

    level: StatusLevel = Field(default=StatusLevel.OK, description="Уровень статуса")
    message: str = Field(..., description="Текстовое сообщение статуса")
    timestamp: datetime = Field(..., description="Время отправки статуса")


class Project(BaseModel):
    """Проект, который может отправлять статусы."""

    id: UUID = Field(..., description="Уникальный идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    token: str = Field(..., description="Уникальный токен проекта для отправки статусов")
    created_at: datetime = Field(..., description="Время создания проекта")
    last_seen: datetime = Field(..., description="Время последнего полученного пульса")
    health: ProjectHealth = Field(
        default=ProjectHealth.ALIVE, description="Текущее состояние проекта"
    )
    statuses: List[Status] = Field(default_factory=list, description="История статусов проекта")
