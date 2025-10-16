"""Модели данных для проектов и статусов в сервисе MishPulse."""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class Status(BaseModel):
    """Статус, отправленный проектом."""

    message: str = Field(..., description="Текстовое сообщение статуса")
    timestamp: datetime = Field(..., description="Время отправки статуса")


class Project(BaseModel):
    """Проект, который может отправлять статусы."""

    id: UUID = Field(..., description="Уникальный идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    token: str = Field(..., description="Уникальный токен проекта для отправки статусов")
    created_at: datetime = Field(..., description="Время создания проекта")
    statuses: List[Status] = Field(default_factory=list, description="История статусов проекта")
