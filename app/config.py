"""Настройки приложения, читаемые из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Конфигурация MishPulse."""

    # Через сколько секунд молчания проект считается «мёртвым»
    dead_after_seconds: float = 300.0
    # Как часто watchdog проверяет пульс проектов
    watchdog_interval_seconds: float = 30.0
    # URL для webhook-уведомлений (если не задан — уведомления только в лог)
    webhook_url: str | None = None


def load_settings() -> Settings:
    """Собрать настройки из переменных окружения с значениями по умолчанию."""

    return Settings(
        dead_after_seconds=float(os.getenv("MISHPULSE_DEAD_AFTER_SECONDS", "300")),
        watchdog_interval_seconds=float(
            os.getenv("MISHPULSE_WATCHDOG_INTERVAL_SECONDS", "30")
        ),
        webhook_url=os.getenv("MISHPULSE_WEBHOOK_URL") or None,
    )


settings = load_settings()
