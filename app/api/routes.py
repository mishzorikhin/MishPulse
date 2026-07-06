"""API router definitions for MishPulse service."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import (
    ProjectCreateRequest,
    ProjectNotificationsSchema,
    ProjectResponse,
    ProjectStateResponse,
    StatusCreateRequest,
    StatusResponse,
)
from ..services import ProjectService, project_service
from .auth import require_admin

router = APIRouter(tags=["system"])


def get_project_service() -> ProjectService:
    """Получить экземпляр сервиса проектов."""

    return project_service


@router.get("/", summary="Service status message")
async def root() -> dict[str, str]:
    """Минимальный эндпоинт для проверки работоспособности."""

    return {"message": "MishPulse backend is running"}


@router.get("/health", summary="Health check")
async def healthcheck() -> dict[str, str]:
    """Простой индикатор здоровья сервиса."""

    return {"status": "ok"}


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=201,
    summary="Создать проект и получить ссылку для статусов",
    dependencies=[Depends(require_admin)],
)
async def create_project(
    payload: ProjectCreateRequest,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Создать новый проект и вернуть ссылку для отправки статусов."""

    project = service.create_project(session, payload.name, payload.notifications)
    link = f"/projects/{project.token}/statuses"
    return ProjectResponse(
        id=project.id,
        name=project.name,
        link=link,
        notifications=ProjectNotificationsSchema(**project.notifications.model_dump()),
    )


@router.get(
    "/projects/summary",
    response_model=list[ProjectStateResponse],
    summary="Сводка состояния всех проектов",
    dependencies=[Depends(require_admin)],
)
async def projects_summary(
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectStateResponse]:
    """Вернуть текущее состояние всех проектов."""

    return [
        ProjectStateResponse(
            id=project.id,
            name=project.name,
            token=project.token,
            health=project.health,
            last_seen=project.last_seen,
            last_message=project.last_message,
        )
        for project in service.get_project_states(session)
    ]


@router.get(
    "/projects/{token}/notifications",
    response_model=ProjectNotificationsSchema,
    summary="Получить настройки уведомлений проекта",
    dependencies=[Depends(require_admin)],
)
async def get_notifications(
    token: str,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> ProjectNotificationsSchema:
    """Вернуть настройки ntfy и Telegram для проекта."""

    notifications = service.get_notifications(session, token)
    return ProjectNotificationsSchema(**notifications.model_dump())


@router.patch(
    "/projects/{token}/notifications",
    response_model=ProjectNotificationsSchema,
    summary="Обновить настройки уведомлений проекта",
    dependencies=[Depends(require_admin)],
)
async def update_notifications(
    token: str,
    payload: ProjectNotificationsSchema,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> ProjectNotificationsSchema:
    """Настроить ntfy-топик и Telegram-бота для алертов о проблемах."""

    project = service.update_notifications(session, token, payload)
    return ProjectNotificationsSchema(**project.notifications.model_dump())


@router.post(
    "/projects/{token}/statuses",
    response_model=StatusResponse,
    summary="Принять статус от проекта",
)
async def push_status(
    token: str,
    payload: StatusCreateRequest,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> StatusResponse:
    """Принять статус по уникальной ссылке проекта (без пароля администратора)."""

    status = service.add_status(session, token, payload)
    return StatusResponse(level=status.level, message=status.message, timestamp=status.timestamp)


@router.get(
    "/projects/{token}/statuses",
    response_model=list[StatusResponse],
    summary="Получить историю статусов проекта",
    dependencies=[Depends(require_admin)],
)
async def list_statuses(
    token: str,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> list[StatusResponse]:
    """Вернуть историю статусов проекта."""

    statuses = service.get_statuses(session, token)
    return [
        StatusResponse(level=s.level, message=s.message, timestamp=s.timestamp)
        for s in statuses
    ]
