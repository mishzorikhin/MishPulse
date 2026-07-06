"""Отправка уведомлений о событиях мониторинга."""

from __future__ import annotations

import json
import logging
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass

from ..config import settings
from ..models import ProjectNotifications

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationTargets:
    """Итоговые адреса доставки с учётом настроек проекта и глобальных значений."""

    ntfy_server: str | None = None
    ntfy_topic: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    webhook_url: str | None = None

    @classmethod
    def from_project(
        cls,
        notifications: ProjectNotifications,
        *,
        webhook_url: str | None = None,
    ) -> "NotificationTargets":
        return cls(
            ntfy_server=notifications.ntfy_server or settings.ntfy_server,
            ntfy_topic=notifications.ntfy_topic,
            telegram_bot_token=notifications.telegram_bot_token or settings.telegram_bot_token,
            telegram_chat_id=notifications.telegram_chat_id,
            webhook_url=webhook_url,
        )


def build_targets(notifications: ProjectNotifications) -> NotificationTargets:
    """Собрать адреса доставки для проекта."""

    return NotificationTargets.from_project(
        notifications,
        webhook_url=settings.webhook_url,
    )


class Notifier:
    """Уведомляет о проблемах: лог, webhook, ntfy и Telegram."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self._default_webhook_url = webhook_url

    def notify_problem(
        self,
        title: str,
        details: dict[str, str],
        targets: NotificationTargets,
        *,
        priority: str = "urgent",
    ) -> None:
        """Отправить алерт о проблеме во все настроенные каналы проекта."""

        body = self._format_body(title, details)
        logger.warning("Алерт: %s | %s", title, details)

        webhook_url = targets.webhook_url or self._default_webhook_url
        if webhook_url:
            self._dispatch(self._send_webhook, webhook_url, title, body)

        if targets.ntfy_topic and targets.ntfy_server:
            self._dispatch(
                self._send_ntfy,
                targets.ntfy_server,
                targets.ntfy_topic,
                title,
                body,
                priority,
            )

        if targets.telegram_chat_id and targets.telegram_bot_token:
            self._dispatch(
                self._send_telegram,
                targets.telegram_bot_token,
                targets.telegram_chat_id,
                title,
                body,
            )

    def notify_recovery(
        self,
        title: str,
        details: dict[str, str],
        targets: NotificationTargets,
    ) -> None:
        """Сообщить о восстановлении — только лог и webhook, без ntfy/Telegram."""

        body = self._format_body(title, details)
        logger.info("Восстановление: %s | %s", title, details)

        webhook_url = targets.webhook_url or self._default_webhook_url
        if webhook_url:
            self._dispatch(self._send_webhook, webhook_url, title, body)

    @staticmethod
    def _format_body(title: str, details: dict[str, str]) -> str:
        lines = [title]
        lines.extend(f"{key}: {value}" for key, value in details.items())
        return "\n".join(lines)

    @staticmethod
    def _dispatch(handler, *args) -> None:
        thread = threading.Thread(target=handler, args=args, daemon=True)
        thread.start()

    @staticmethod
    def _send_webhook(webhook_url: str, title: str, body: str) -> None:
        payload = json.dumps({"title": title, "message": body}).encode("utf-8")
        request = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
            logger.info("Webhook-уведомление отправлено: %s", title)
        except Exception:
            logger.exception("Не удалось отправить webhook-уведомление")

    @staticmethod
    def _send_ntfy(
        server: str,
        topic: str,
        title: str,
        body: str,
        priority: str,
    ) -> None:
        url = f"{server.rstrip('/')}/{urllib.parse.quote(topic, safe='')}"
        request = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "warning,skull",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
            logger.info("ntfy-уведомление отправлено в %s: %s", topic, title)
        except Exception:
            logger.exception("Не удалось отправить ntfy-уведомление в %s", topic)

    @staticmethod
    def _send_telegram(bot_token: str, chat_id: str, title: str, body: str) -> None:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        text = f"<b>{title}</b>\n{body}"
        payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode(
            "utf-8"
        )
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
            logger.info("Telegram-уведомление отправлено в chat %s: %s", chat_id, title)
        except Exception:
            logger.exception("Не удалось отправить Telegram-уведомление в chat %s", chat_id)


notifier = Notifier(webhook_url=settings.webhook_url)
