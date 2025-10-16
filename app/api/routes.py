"""API router definitions for MishPulse service."""

from fastapi import APIRouter, Depends

from ..schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    StatusCreateRequest,
    StatusResponse,
)
from ..services import ProjectService, project_service

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
    summary="Создать проект и получить ссылку для статусов",
)
async def create_project(
    payload: ProjectCreateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Создать новый проект и вернуть ссылку для отправки статусов."""

    project = service.create_project(payload.name)
    link = f"/projects/{project.token}/statuses"
    return ProjectResponse(id=project.id, name=project.name, link=link)


@router.post(
    "/projects/{token}/statuses",
    response_model=StatusResponse,
    summary="Принять статус от проекта",
)
async def push_status(
    token: str,
    payload: StatusCreateRequest,
    service: ProjectService = Depends(get_project_service),
) -> StatusResponse:
    """Принять статус по уникальной ссылке проекта."""

    status = service.add_status(token, payload)
    return StatusResponse(message=status.message, timestamp=status.timestamp)


@router.get(
    "/projects/{token}/statuses",
    response_model=list[StatusResponse],
    summary="Получить историю статусов проекта",
)
async def list_statuses(
    token: str,
    service: ProjectService = Depends(get_project_service),
) -> list[StatusResponse]:
    """Вернуть историю статусов проекта."""

    statuses = service.get_statuses(token)
    return [StatusResponse(message=s.message, timestamp=s.timestamp) for s in statuses]
