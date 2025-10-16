"""Сервис управления проектами и их статусами."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException

from ..models import Project, Status
from ..schemas import StatusCreateRequest

logger = logging.getLogger(__name__)


class ProjectService:
    """Сервис для работы с проектами."""

    def __init__(self) -> None:
        # Хранилище проектов по токену
        self._projects: Dict[str, Project] = {}
        # Блокировка для потокобезопасного доступа
        self._lock = RLock()

    def create_project(self, name: str) -> Project:
        """Создать новый проект и сгенерировать уникальную ссылку."""

        with self._lock:
            token = uuid4().hex
            project_id = uuid4()
            project = Project(
                id=project_id,
                name=name,
                token=token,
                created_at=datetime.now(timezone.utc),
            )
            self._projects[token] = project
            logger.info("Создан проект %s с токеном %s", project_id, token)
            return project

    def add_status(self, token: str, payload: StatusCreateRequest) -> Status:
        """Добавить новый статус проекту."""

        with self._lock:
            project = self._projects.get(token)
            if project is None:
                logger.warning("Попытка отправить статус для неизвестного токена %s", token)
                raise HTTPException(status_code=404, detail="Проект не найден")

            # Используем текущее время, если оно не было передано
            timestamp = payload.timestamp or datetime.now(timezone.utc)

            # Проверяем, что время статуса не меньше последнего полученного
            if project.statuses and timestamp <= project.statuses[-1].timestamp:
                logger.error(
                    "Получен статус с прошедшим временем от проекта %s: %s <= %s",
                    project.id,
                    timestamp,
                    project.statuses[-1].timestamp,
                )
                raise HTTPException(status_code=400, detail="Время статуса должно увеличиваться")

            status = Status(message=payload.message, timestamp=timestamp)
            project.statuses.append(status)
            logger.info("Добавлен статус для проекта %s", project.id)

        # После сохранения статуса отправляем его пользователю
        self._deliver_status(project, status)
        return status

    def _deliver_status(self, project: Project, status: Status) -> None:
        """Отправить статус пользователю (пока выводим в консоль)."""

        logger.debug("Отправляем статус проекта %s в консоль", project.id)
        print(
            f"[Проект {project.name} ({project.id})] {status.timestamp.isoformat()}: {status.message}",
            flush=True,
        )

    def get_statuses(self, token: str) -> list[Status]:
        """Получить список статусов проекта по токену."""

        with self._lock:
            project = self._projects.get(token)
            if project is None:
                logger.warning("Запрошены статусы неизвестного токена %s", token)
                raise HTTPException(status_code=404, detail="Проект не найден")
            # Возвращаем копию списка для защиты внутреннего состояния
            return list(project.statuses)


# Создаем единственный экземпляр сервиса для использования в обработчиках
project_service = ProjectService()
