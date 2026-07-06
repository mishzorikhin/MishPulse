"""Схемы авторизации."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthLoginRequest(BaseModel):
    """Запрос на вход по паролю."""

    password: str = Field(..., min_length=1, description="Пароль администратора")


class AuthStatusResponse(BaseModel):
    """Статус авторизации для UI и клиентов."""

    required: bool = Field(..., description="Включена ли проверка пароля")
    authenticated: bool = Field(..., description="Передан ли верный пароль в запросе")
