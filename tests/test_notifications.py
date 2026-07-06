"""Тесты уведомлений ntfy и Telegram."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.notifier import NotificationTargets, Notifier


@pytest.fixture()
def notifier() -> Notifier:
    return Notifier()


def test_notify_problem_sends_ntfy_and_telegram(notifier: Notifier) -> None:
    targets = NotificationTargets(
        ntfy_server="https://ntfy.example",
        ntfy_topic="alerts",
        telegram_bot_token="bot123",
        telegram_chat_id="-1001",
    )
    with patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value = MagicMock()
        notifier.notify_problem("Сбой", {"message": "boom"}, targets)

    assert urlopen.call_count == 2
    ntfy_request = urlopen.call_args_list[0].args[0]
    telegram_request = urlopen.call_args_list[1].args[0]

    assert ntfy_request.full_url == "https://ntfy.example/alerts"
    assert ntfy_request.get_header("Priority") == "urgent"
    assert "Сбой" in ntfy_request.get_header("Title")

    assert telegram_request.full_url == "https://api.telegram.org/botbot123/sendMessage"
    assert b'"chat_id": "-1001"' in telegram_request.data


def test_notify_problem_skips_channels_when_not_configured(notifier: Notifier) -> None:
    targets = NotificationTargets()
    with patch("urllib.request.urlopen") as urlopen:
        notifier.notify_problem("Сбой", {"message": "boom"}, targets)
    urlopen.assert_not_called()


def test_create_project_with_notifications(client) -> None:
    response = client.post(
        "/projects",
        json={
            "name": "api",
            "notifications": {
                "ntfy_topic": "mishpulse-api",
                "telegram_chat_id": "12345",
                "telegram_bot_token": "token",
            },
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["notifications"]["ntfy_topic"] == "mishpulse-api"
    assert body["notifications"]["telegram_chat_id"] == "12345"


def test_update_and_get_notifications(client) -> None:
    create = client.post("/projects", json={"name": "svc"})
    token = create.json()["link"].split("/")[2]

    patch_response = client.patch(
        f"/projects/{token}/notifications",
        json={"ntfy_topic": "svc-alerts", "ntfy_server": "https://ntfy.local"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["ntfy_topic"] == "svc-alerts"

    get_response = client.get(f"/projects/{token}/notifications")
    assert get_response.status_code == 200
    assert get_response.json()["ntfy_server"] == "https://ntfy.local"


def test_error_status_uses_project_notification_targets(client, recording_notifier) -> None:
    create = client.post(
        "/projects",
        json={
            "name": "worker",
            "notifications": {"ntfy_topic": "worker-alerts", "telegram_chat_id": "99"},
        },
    )
    link = create.json()["link"]

    response = client.post(link, json={"level": "error", "message": "disk full"})
    assert response.status_code == 200

    assert len(recording_notifier.problems) == 1
    _, details, targets, priority = recording_notifier.problems[0]
    assert details["message"] == "disk full"
    assert targets.ntfy_topic == "worker-alerts"
    assert targets.telegram_chat_id == "99"
    assert priority == "urgent"
