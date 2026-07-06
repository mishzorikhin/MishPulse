"""Репозиторий проектов и статусов."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models import Project, ProjectHealth, ProjectNotifications, Status, StatusLevel
from ..db.orm import ProjectORM, StatusORM


def _notifications_from_row(project: ProjectORM) -> ProjectNotifications:
    return ProjectNotifications(
        ntfy_server=project.ntfy_server,
        ntfy_topic=project.ntfy_topic,
        telegram_bot_token=project.telegram_bot_token,
        telegram_chat_id=project.telegram_chat_id,
    )


def _apply_notifications(row: ProjectORM, notifications: ProjectNotifications | None) -> None:
    if notifications is None:
        return
    row.ntfy_server = notifications.ntfy_server
    row.ntfy_topic = notifications.ntfy_topic
    row.telegram_bot_token = notifications.telegram_bot_token
    row.telegram_chat_id = notifications.telegram_chat_id


def _to_domain(project: ProjectORM, statuses: list[StatusORM] | None = None) -> Project:
    """Собрать доменную модель проекта из ORM."""

    return Project(
        id=project.id,
        name=project.name,
        token=project.token,
        created_at=project.created_at,
        last_seen=project.last_seen,
        health=ProjectHealth(project.health),
        last_message=project.last_message,
        notifications=_notifications_from_row(project),
        statuses=[
            Status(level=StatusLevel(row.level), message=row.message, timestamp=row.timestamp)
            for row in (statuses if statuses is not None else project.statuses)
        ],
    )


class ProjectRepository:
    """Доступ к проектам и статусам в БД."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_project(
        self,
        name: str,
        *,
        now: datetime,
        notifications: ProjectNotifications | None = None,
    ) -> Project:
        """Создать проект с уникальным токеном."""

        row = ProjectORM(
            id=uuid4(),
            name=name,
            token=uuid4().hex,
            created_at=now,
            last_seen=now,
            health=ProjectHealth.ALIVE.value,
        )
        _apply_notifications(row, notifications)
        self._session.add(row)
        self._session.flush()
        return _to_domain(row, statuses=[])

    def get_by_token(self, token: str) -> ProjectORM | None:
        return self._session.scalar(select(ProjectORM).where(ProjectORM.token == token))

    def get_project(self, token: str) -> Project | None:
        row = self.get_by_token(token)
        return _to_domain(row) if row else None

    def update_notifications(
        self,
        token: str,
        notifications: ProjectNotifications,
    ) -> Project | None:
        row = self.get_by_token(token)
        if row is None:
            return None
        _apply_notifications(row, notifications)
        self._session.flush()
        return _to_domain(row, statuses=[])

    def list_projects(self) -> list[Project]:
        rows = self._session.scalars(select(ProjectORM).order_by(ProjectORM.created_at)).all()
        return [_to_domain(row, statuses=[]) for row in rows]

    def list_statuses(self, project_id: UUID) -> list[Status]:
        rows = self._session.scalars(
            select(StatusORM)
            .where(StatusORM.project_id == project_id)
            .order_by(StatusORM.timestamp)
        ).all()
        return [
            Status(level=StatusLevel(row.level), message=row.message, timestamp=row.timestamp)
            for row in rows
        ]

    def get_last_status(self, project_id: UUID) -> StatusORM | None:
        return self._session.scalar(
            select(StatusORM)
            .where(StatusORM.project_id == project_id)
            .order_by(StatusORM.timestamp.desc())
            .limit(1)
        )

    def add_status(self, project: ProjectORM, status: Status) -> Status:
        """Сохранить статус и обновить агрегаты проекта."""

        row = StatusORM(
            project_id=project.id,
            level=status.level.value,
            message=status.message,
            timestamp=status.timestamp,
        )
        self._session.add(row)
        project.last_seen = status.timestamp
        project.last_message = status.message
        project.health = {
            StatusLevel.OK: ProjectHealth.ALIVE,
            StatusLevel.WARNING: ProjectHealth.WARNING,
            StatusLevel.ERROR: ProjectHealth.ERROR,
        }[status.level].value
        self._session.flush()
        return status

    def mark_dead_before(self, threshold: datetime) -> list[Project]:
        """Пометить молчащие проекты как dead и вернуть только что помеченные."""

        rows = self._session.scalars(
            update(ProjectORM)
            .where(ProjectORM.health != ProjectHealth.DEAD.value)
            .where(ProjectORM.last_seen < threshold)
            .values(health=ProjectHealth.DEAD.value)
            .returning(ProjectORM)
        ).all()
        return [_to_domain(row, statuses=[]) for row in rows]

    def set_last_seen(self, token: str, last_seen: datetime) -> ProjectORM | None:
        """Обновить last_seen (для тестов и служебных сценариев)."""

        project = self.get_by_token(token)
        if project is None:
            return None
        project.last_seen = last_seen
        self._session.flush()
        return project

    def get_health(self, token: str) -> ProjectHealth | None:
        project = self.get_by_token(token)
        return ProjectHealth(project.health) if project else None
