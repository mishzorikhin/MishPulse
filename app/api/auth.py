"""Простая авторизация по паролю администратора."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import settings
from ..schemas import AuthLoginRequest, AuthStatusResponse

router = APIRouter(tags=["auth"])


def _extract_password(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ")
    return request.headers.get("X-MishPulse-Password")


def is_authenticated(request: Request) -> bool:
    """Проверить, что запрос содержит верный пароль (или авторизация отключена)."""

    if not settings.admin_password:
        return True
    password = _extract_password(request)
    if password is None:
        return False
    return secrets.compare_digest(password, settings.admin_password)


def require_admin(request: Request) -> None:
    """Зависимость FastAPI: требовать пароль администратора."""

    if is_authenticated(request):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется авторизация",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/auth/status", response_model=AuthStatusResponse)
async def auth_status(request: Request) -> AuthStatusResponse:
    """Проверить, включена ли авторизация и валиден ли текущий пароль."""

    return AuthStatusResponse(
        required=bool(settings.admin_password),
        authenticated=is_authenticated(request),
    )


@router.post("/auth/login", response_model=AuthStatusResponse)
async def auth_login(payload: AuthLoginRequest, request: Request) -> AuthStatusResponse:
    """Проверить пароль (для входа в веб-интерфейс)."""

    if not settings.admin_password:
        return AuthStatusResponse(required=False, authenticated=True)

    if not secrets.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный пароль")

    return AuthStatusResponse(required=True, authenticated=True)
