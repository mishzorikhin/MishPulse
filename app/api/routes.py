"""API router definitions for MishPulse service."""

from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ProjectHealth
from ..schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectStateResponse,
    StatusCreateRequest,
    StatusResponse,
)
from ..services import ProjectService, project_service

router = APIRouter(tags=["system"])

_HEALTH_ICONS = {
    ProjectHealth.ALIVE: "🟢",
    ProjectHealth.WARNING: "🟠",
    ProjectHealth.ERROR: "🟠",
    ProjectHealth.DEAD: "🔴",
}


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
)
async def create_project(
    payload: ProjectCreateRequest,
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Создать новый проект и вернуть ссылку для отправки статусов."""

    project = service.create_project(session, payload.name)
    link = f"/projects/{project.token}/statuses"
    return ProjectResponse(id=project.id, name=project.name, link=link)


@router.get(
    "/projects/summary",
    response_model=list[ProjectStateResponse],
    summary="Сводка состояния всех проектов",
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
            health=project.health,
            last_seen=project.last_seen,
            last_message=project.last_message,
        )
        for project in service.get_project_states(session)
    ]


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Минимальный HTML-дашборд состояния проектов",
)
async def dashboard(
    session: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> HTMLResponse:
    """Простая HTML-страница со статусами всех проектов."""

    rows = []
    for project in service.get_project_states(session):
        icon = _HEALTH_ICONS[project.health]
        rows.append(
            "<tr>"
            f"<td>{icon} {escape(project.name)}</td>"
            f"<td>{escape(project.health.value)}</td>"
            f"<td>{escape(project.last_seen.strftime('%Y-%m-%d %H:%M:%S %Z'))}</td>"
            f"<td>{escape(project.last_message or '')}</td>"
            "</tr>"
        )
    body = "".join(rows) or '<tr><td colspan="4">Проектов пока нет</td></tr>'
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="30">
  <title>MishPulse — дашборд</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f7f7f9; color: #222; }}
    h1 {{ font-size: 1.4rem; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
    th, td {{ padding: .6rem .9rem; border-bottom: 1px solid #e5e5ea; text-align: left; }}
    th {{ background: #fafafa; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>MishPulse — состояние проектов</h1>
  <table>
    <thead><tr><th>Проект</th><th>Состояние</th><th>Последний пульс</th><th>Последнее сообщение</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</body>
</html>"""
    return HTMLResponse(html)


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
    """Принять статус по уникальной ссылке проекта."""

    status = service.add_status(session, token, payload)
    return StatusResponse(level=status.level, message=status.message, timestamp=status.timestamp)


@router.get(
    "/projects/{token}/statuses",
    response_model=list[StatusResponse],
    summary="Получить историю статусов проекта",
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
