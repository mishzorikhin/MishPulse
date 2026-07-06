"""Сервис управления проектами и их статусами."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Project, ProjectNotifications, Status, StatusLevel
from ..repositories import ProjectRepository
from ..repositories.project_repository import _notifications_from_row
from ..schemas import ProjectNotificationsSchema, StatusCreateRequest
from .notifier import Notifier, build_targets, notifier as default_notifier

logger = logging.getLogger(__name__)


def _to_utc(moment: datetime) -> datetime:
    """Привести время к UTC; наивное время трактуем как UTC."""

    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _to_notifications(schema: ProjectNotificationsSchema | None) -> ProjectNotifications | None:
    if schema is None:
        return None
    return ProjectNotifications(**schema.model_dump())


class ProjectService:
    """Сервис для работы с проектами."""

    def __init__(self, notifier: Notifier | None = None) -> None:
        self._notifier = notifier or default_notifier

    def create_project(
        self,
        session: Session,
        name: str,
        notifications: ProjectNotificationsSchema | None = None,
    ) -> Project:
        """Создать новый проект и сгенерировать уникальную ссылку."""

        repo = ProjectRepository(session)
        now = datetime.now(timezone.utc)
        project = repo.create_project(name, now=now, notifications=_to_notifications(notifications))
        session.commit()
        logger.info("Создан проект %s с токеном %s", project.id, project.token)
        return project

    def update_notifications(
        self,
        session: Session,
        token: str,
        notifications: ProjectNotificationsSchema,
    ) -> Project:
        """Обновить настройки уведомлений проекта."""

        repo = ProjectRepository(session)
        project = repo.update_notifications(token, ProjectNotifications(**notifications.model_dump()))
        if project is None:
            raise HTTPException(status_code=404, detail="Проект не найден")
        session.commit()
        logger.info("Обновлены уведомления проекта %s", project.id)
        return project

    def get_notifications(self, session: Session, token: str) -> ProjectNotifications:
        """Получить настройки уведомлений проекта."""

        repo = ProjectRepository(session)
        project = repo.get_project(token)
        if project is None:
            raise HTTPException(status_code=404, detail="Проект не найден")
        return project.notifications

    def add_status(self, session: Session, token: str, payload: StatusCreateRequest) -> Status:
        """Добавить новый статус проекту."""

        repo = ProjectRepository(session)
        project_row = repo.get_by_token(token)
        if project_row is None:
            logger.warning("Запрос с неизвестным токеном %s", token)
            raise HTTPException(status_code=404, detail="Проект не найден")

        timestamp = _to_utc(payload.timestamp or datetime.now(timezone.utc))
        last_status = repo.get_last_status(project_row.id)
        if last_status is not None and timestamp <= _to_utc(last_status.timestamp):
            logger.error(
                "Получен статус с прошедшим временем от проекта %s: %s <= %s",
                project_row.id,
                timestamp,
                last_status.timestamp,
            )
            raise HTTPException(status_code=400, detail="Время статуса должно увеличиваться")

        was_dead = project_row.health == "dead"
        status = Status(level=payload.level, message=payload.message, timestamp=timestamp)
        repo.add_status(project_row, status)
        session.commit()
        logger.info("Добавлен статус для проекта %s (%s)", project_row.id, status.level.value)

        targets = build_targets(_notifications_from_row(project_row))
        details = {
            "project": str(project_row.id),
            "message": status.message,
            "timestamp": status.timestamp.isoformat(),
        }

        if status.level is StatusLevel.ERROR:
            self._notifier.notify_problem(
                f"Проект «{project_row.name}» сообщил об ошибке",
                details,
                targets,
                priority="urgent",
            )
        elif status.level is StatusLevel.WARNING:
            self._notifier.notify_problem(
                f"Проект «{project_row.name}» предупреждает",
                details,
                targets,
                priority="high",
            )
        elif was_dead:
            self._notifier.notify_recovery(
                f"Проект «{project_row.name}» снова на связи",
                {
                    "project": str(project_row.id),
                    "timestamp": status.timestamp.isoformat(),
                },
                targets,
            )
        return status

    def get_statuses(self, session: Session, token: str) -> list[Status]:
        """Получить список статусов проекта по токену."""

        repo = ProjectRepository(session)
        project_row = repo.get_by_token(token)
        if project_row is None:
            logger.warning("Запрошены статусы неизвестного токена %s", token)
            raise HTTPException(status_code=404, detail="Проект не найден")
        return repo.list_statuses(project_row.id)

    def get_project_states(self, session: Session) -> list[Project]:
        """Вернуть снимок всех проектов для сводки/дашборда."""

        return ProjectRepository(session).list_projects()

    def mark_dead_projects(
        self,
        session: Session | None = None,
        dead_after_seconds: float | None = None,
    ) -> list[Project]:
        """Пометить проекты без пульса как «мёртвые» и уведомить о них."""

        timeout = dead_after_seconds if dead_after_seconds is not None else settings.dead_after_seconds
        threshold = datetime.now(timezone.utc) - timedelta(seconds=timeout)
        own_session = session is None
        from ..db.session import SessionLocal

        db = session or SessionLocal()
        try:
            repo = ProjectRepository(db)
            newly_dead = repo.mark_dead_before(threshold)
            for project in newly_dead:
                logger.warning("Проект %s помечен как мёртвый", project.id)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            if own_session:
                db.close()

        for project in newly_dead:
            self._notifier.notify_problem(
                f"Проект «{project.name}» не отвечает",
                {
                    "project": str(project.id),
                    "last_seen": project.last_seen.isoformat(),
                },
                build_targets(project.notifications),
                priority="urgent",
            )
        return newly_dead

    def set_last_seen(self, session: Session, token: str, last_seen: datetime) -> None:
        """Обновить время последнего пульса (используется в тестах)."""

        repo = ProjectRepository(session)
        if repo.set_last_seen(token, last_seen) is None:
            raise HTTPException(status_code=404, detail="Проект не найден")
        session.commit()

    def get_health(self, session: Session, token: str):
        """Получить текущее состояние проекта."""

        repo = ProjectRepository(session)
        health = repo.get_health(token)
        if health is None:
            raise HTTPException(status_code=404, detail="Проект не найден")
        return health


# Создаем единственный экземпляр сервиса для использования в обработчиках
project_service = ProjectService()
