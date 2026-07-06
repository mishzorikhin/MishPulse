"""Сервис управления проектами и их статусами."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException

from ..config import settings
from ..models import Project, ProjectHealth, Status, StatusLevel
from ..schemas import StatusCreateRequest
from .notifier import Notifier, notifier as default_notifier

logger = logging.getLogger(__name__)


def _to_utc(moment: datetime) -> datetime:
    """Привести время к UTC; наивное время трактуем как UTC."""

    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


class ProjectService:
    """Сервис для работы с проектами."""

    def __init__(self, notifier: Notifier | None = None) -> None:
        # Хранилище проектов по токену
        self._projects: Dict[str, Project] = {}
        # Блокировка для потокобезопасного доступа
        self._lock = RLock()
        self._notifier = notifier or default_notifier

    def create_project(self, name: str) -> Project:
        """Создать новый проект и сгенерировать уникальную ссылку."""

        with self._lock:
            token = uuid4().hex
            project_id = uuid4()
            now = datetime.now(timezone.utc)
            project = Project(
                id=project_id,
                name=name,
                token=token,
                created_at=now,
                last_seen=now,
            )
            self._projects[token] = project
            logger.info("Создан проект %s с токеном %s", project_id, token)
            return project

    def add_status(self, token: str, payload: StatusCreateRequest) -> Status:
        """Добавить новый статус проекту."""

        with self._lock:
            project = self._get_project_or_404(token)

            # Используем текущее время, если оно не было передано
            timestamp = _to_utc(payload.timestamp or datetime.now(timezone.utc))

            # Проверяем, что время статуса не меньше последнего полученного
            if project.statuses and timestamp <= project.statuses[-1].timestamp:
                logger.error(
                    "Получен статус с прошедшим временем от проекта %s: %s <= %s",
                    project.id,
                    timestamp,
                    project.statuses[-1].timestamp,
                )
                raise HTTPException(status_code=400, detail="Время статуса должно увеличиваться")

            status = Status(level=payload.level, message=payload.message, timestamp=timestamp)
            project.statuses.append(status)
            project.last_seen = timestamp
            was_dead = project.health is ProjectHealth.DEAD
            project.health = {
                StatusLevel.OK: ProjectHealth.ALIVE,
                StatusLevel.WARNING: ProjectHealth.WARNING,
                StatusLevel.ERROR: ProjectHealth.ERROR,
            }[status.level]
            logger.info("Добавлен статус для проекта %s (%s)", project.id, status.level.value)

        if status.level is StatusLevel.ERROR:
            self._notifier.notify(
                f"Проект «{project.name}» сообщил об ошибке",
                {
                    "project": str(project.id),
                    "message": status.message,
                    "timestamp": status.timestamp.isoformat(),
                },
            )
        elif was_dead:
            self._notifier.notify(
                f"Проект «{project.name}» снова на связи",
                {
                    "project": str(project.id),
                    "timestamp": status.timestamp.isoformat(),
                },
            )
        return status

    def get_statuses(self, token: str) -> list[Status]:
        """Получить список статусов проекта по токену."""

        with self._lock:
            project = self._get_project_or_404(token)
            # Возвращаем копию списка для защиты внутреннего состояния
            return list(project.statuses)

    def get_project_states(self) -> list[Project]:
        """Вернуть снимок всех проектов для сводки/дашборда."""

        with self._lock:
            return [project.model_copy(deep=True) for project in self._projects.values()]

    def mark_dead_projects(self, dead_after_seconds: float | None = None) -> list[Project]:
        """Пометить проекты без пульса как «мёртвые» и уведомить о них.

        Возвращает список проектов, которые перешли в состояние DEAD на этом проходе.
        """

        timeout = dead_after_seconds if dead_after_seconds is not None else settings.dead_after_seconds
        now = datetime.now(timezone.utc)
        newly_dead: list[Project] = []

        with self._lock:
            for project in self._projects.values():
                if project.health is ProjectHealth.DEAD:
                    continue
                silence = (now - project.last_seen).total_seconds()
                if silence > timeout:
                    project.health = ProjectHealth.DEAD
                    newly_dead.append(project)
                    logger.warning(
                        "Проект %s молчит %.0f сек. и помечен как мёртвый",
                        project.id,
                        silence,
                    )

        for project in newly_dead:
            self._notifier.notify(
                f"Проект «{project.name}» не отвечает",
                {
                    "project": str(project.id),
                    "last_seen": project.last_seen.isoformat(),
                },
            )
        return newly_dead

    def _get_project_or_404(self, token: str) -> Project:
        project = self._projects.get(token)
        if project is None:
            logger.warning("Запрос с неизвестным токеном %s", token)
            raise HTTPException(status_code=404, detail="Проект не найден")
        return project


# Создаем единственный экземпляр сервиса для использования в обработчиках
project_service = ProjectService()
