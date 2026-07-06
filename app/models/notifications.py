"""Настройки уведомлений проекта."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectNotifications(BaseModel):
    """Каналы уведомлений, настраиваемые для каждого проекта."""

    ntfy_server: str | None = Field(
        default=None,
        description="Базовый URL ntfy-сервера (если не задан — берётся из MISHPULSE_NTFY_SERVER)",
    )
    ntfy_topic: str | None = Field(
        default=None,
        description="Топик ntfy для алертов о проблемах",
    )
    telegram_bot_token: str | None = Field(
        default=None,
        description="Токен Telegram-бота (если не задан — берётся из MISHPULSE_TELEGRAM_BOT_TOKEN)",
    )
    telegram_chat_id: str | None = Field(
        default=None,
        description="Chat ID, куда бот отправляет сообщения",
    )

    def has_ntfy(self) -> bool:
        return bool(self.ntfy_topic)

    def has_telegram(self) -> bool:
        return bool(self.telegram_chat_id)
