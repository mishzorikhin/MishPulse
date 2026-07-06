"""API router definitions for MishPulse service."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import (
    MaintenanceCleanupResponse,
    ProjectCreateRequest,
    ProjectNotificationsSchema,
    ProjectResponse,
    ProjectStateResponse,
    ProjectUpdateRequest,
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

    project = service.create_project(
        session,
        payload.name,
        payload.timeout_seconds,
        payload.retention_days,
        payload.notifications,
    )
    link = f"/projects/{project.token}/statuses"
    return ProjectResponse(
        id=project.id,
        name=project.name,
        link=link,
        enabled=project.enabled,
        timeout_seconds=project.timeout_seconds,
        retention_days=project.retention_days,
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
            enabled=project.enabled,
            timeout_seconds=project.timeout_seconds,
            retention_days=project.retention_days,
            last_seen=project.last_seen,
            last_message=project.last_message,
        )
        for project in service.get_project_states(session)
    ]


@router.patch(
    "/projects/{token}",
    response_model=ProjectStateResponse,
    summary="Обновить настройки проекта",
    dependencies=[Depends(require_admin)],
)
async def update_project(
    token: str,
    payload: ProjectUpdateRequest,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> ProjectStateResponse:
    """Обновить имя, enabled, timeout и retention проекта."""

    project = service.update_project(session, token, payload)
    return ProjectStateResponse(
        id=project.id,
        name=project.name,
        token=project.token,
        health=project.health,
        enabled=project.enabled,
        timeout_seconds=project.timeout_seconds,
        retention_days=project.retention_days,
        last_seen=project.last_seen,
        last_message=project.last_message,
    )


@router.delete(
    "/projects/{token}",
    status_code=204,
    summary="Удалить проект",
    dependencies=[Depends(require_admin)],
)
async def delete_project(
    token: str,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> Response:
    """Удалить проект и всю историю статусов."""

    service.delete_project(session, token)
    return Response(status_code=204)


@router.post(
    "/projects/{token}/test-notification",
    status_code=204,
    summary="Отправить тестовое уведомление",
    dependencies=[Depends(require_admin)],
)
async def send_test_notification(
    token: str,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> Response:
    """Проверить ntfy/Telegram/webhook настройки проекта тестовым алертом."""

    service.send_test_notification(session, token)
    return Response(status_code=204)


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


@router.post(
    "/maintenance/cleanup-statuses",
    response_model=MaintenanceCleanupResponse,
    summary="Удалить старую историю статусов",
    dependencies=[Depends(require_admin)],
)
async def cleanup_status_history(
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> MaintenanceCleanupResponse:
    """Запустить retention cleanup вручную."""

    deleted = service.cleanup_old_statuses(session)
    return MaintenanceCleanupResponse(deleted_statuses=deleted)
