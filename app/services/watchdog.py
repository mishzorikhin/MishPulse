"""Фоновая проверка пульса проектов."""

from __future__ import annotations

import asyncio
import logging

from ..config import settings
from .project_service import ProjectService

logger = logging.getLogger(__name__)


class Watchdog:
    """Периодически проверяет, какие проекты перестали подавать признаки жизни."""

    def __init__(
        self,
        service: ProjectService,
        interval_seconds: float | None = None,
    ) -> None:
        self._service = service
        self._interval = (
            interval_seconds
            if interval_seconds is not None
            else settings.watchdog_interval_seconds
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Запустить фоновую задачу проверки."""

        if self._task is not None:
            return
        self._task = asyncio.get_running_loop().create_task(self._run())
        logger.info("Watchdog запущен, интервал %.0f сек.", self._interval)

    async def stop(self) -> None:
        """Остановить фоновую задачу."""

        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Watchdog остановлен")

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                self._service.mark_dead_projects()
                self._service.cleanup_old_statuses()
            except Exception:
                logger.exception("Ошибка при проверке пульса проектов")
