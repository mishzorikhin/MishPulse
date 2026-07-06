"""Репозиторий проектов и статусов."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
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
        enabled=project.enabled,
        timeout_seconds=project.timeout_seconds,
        retention_days=project.retention_days,
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
        timeout_seconds: float | None = None,
        retention_days: int | None = None,
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
            enabled=True,
            timeout_seconds=timeout_seconds,
            retention_days=retention_days,
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

    def update_project(
        self,
        token: str,
        *,
        name: str | None = None,
        enabled: bool | None = None,
        timeout_seconds: float | None = None,
        retention_days: int | None = None,
        update_timeout: bool = False,
        update_retention: bool = False,
    ) -> Project | None:
        """Обновить основные настройки проекта."""

        row = self.get_by_token(token)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if enabled is not None:
            row.enabled = enabled
        if update_timeout:
            row.timeout_seconds = timeout_seconds
        if update_retention:
            row.retention_days = retention_days
        self._session.flush()
        return _to_domain(row, statuses=[])

    def delete_project(self, token: str) -> bool:
        """Удалить проект вместе с историей статусов."""

        row = self.get_by_token(token)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

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

    def list_watchdog_candidates(self) -> list[ProjectORM]:
        """Вернуть включённые проекты, которые ещё не помечены как dead."""

        return list(
            self._session.scalars(
                select(ProjectORM)
                .where(ProjectORM.enabled.is_(True))
                .where(ProjectORM.health != ProjectHealth.DEAD.value)
            ).all()
        )

    def mark_dead(self, project: ProjectORM) -> Project:
        """Пометить проект как dead."""

        project.health = ProjectHealth.DEAD.value
        self._session.flush()
        return _to_domain(project, statuses=[])

    def prune_statuses_before(self, project_id: UUID, cutoff: datetime) -> int:
        """Удалить статусы проекта старше cutoff."""

        result = self._session.execute(
            delete(StatusORM)
            .where(StatusORM.project_id == project_id)
            .where(StatusORM.timestamp < cutoff)
        )
        return int(result.rowcount or 0)

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
