""" Отправка уведомлений о событиях мониторинга."""

from __future__ import annotations

import json
import logging
import threading
import urllib.request

from ..config import settings

logger = logging.getLogger(__name__)


class Notifier:
    """Уведомляет о событиях: пишет в лог и, если настроен, шлёт webhook."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self._webhook_url = webhook_url

    def notify(self, title: str, details: dict[str, str]) -> None:
        """Отправить уведомление во все настроенные каналы."""

        logger.warning("Уведомление: %s | %s", title, details)
        if self._webhook_url:
            # Webhook отправляем в отдельном потоке, чтобы не блокировать обработку запроса
            thread = threading.Thread(
                target=self._send_webhook,
                args=(title, details),
                daemon=True,
            )
            thread.start()

    def _send_webhook(self, title: str, details: dict[str, str]) -> None:
        payload = json.dumps({"title": title, **details}).encode("utf-8")
        request = urllib.request.Request(
            self._webhook_url,
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


notifier = Notifier(webhook_url=settings.webhook_url)
