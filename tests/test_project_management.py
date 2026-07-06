"""Тесты управления проектами: timeout, enabled, delete, retention."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import ProjectHealth
from app.schemas import ProjectUpdateRequest, StatusCreateRequest


def _create(client, name: str = "managed") -> tuple[str, str]:
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    link = response.json()["link"]
    token = link.split("/")[2]
    return token, link


def test_update_project_settings(client) -> None:
    token, _ = _create(client)

    response = client.patch(
        f"/projects/{token}",
        json={
            "name": "renamed",
            "enabled": False,
            "timeout_seconds": 42,
            "retention_days": 7,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "renamed"
    assert body["enabled"] is False
    assert body["timeout_seconds"] == 42
    assert body["retention_days"] == 7


def test_disabled_project_rejects_heartbeat(client) -> None:
    token, link = _create(client)
    assert client.patch(f"/projects/{token}", json={"enabled": False}).status_code == 200

    response = client.post(link, json={"message": "alive"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Проект отключён"


def test_delete_project_removes_it(client) -> None:
    token, link = _create(client)

    assert client.delete(f"/projects/{token}").status_code == 204
    assert client.get("/projects/summary").json() == []
    assert client.post(link, json={"message": "alive"}).status_code == 404


def test_test_notification_uses_project_targets(client, recording_notifier) -> None:
    token, _ = _create(client)
    client.patch(
        f"/projects/{token}/notifications",
        json={"ntfy_topic": "managed-alerts", "telegram_chat_id": "42"},
    )

    response = client.post(f"/projects/{token}/test-notification")

    assert response.status_code == 204
    assert len(recording_notifier.problems) == 1
    title, details, targets, priority = recording_notifier.problems[0]
    assert "Тестовый алерт" in title
    assert details["message"] == "Проверка настроек уведомлений MishPulse"
    assert targets.ntfy_topic == "managed-alerts"
    assert targets.telegram_chat_id == "42"
    assert priority == "high"


def test_project_specific_timeout_marks_dead(service, db_session) -> None:
    project = service.create_project(db_session, "fast", timeout_seconds=10)
    service.set_last_seen(
        db_session,
        project.token,
        datetime.now(timezone.utc) - timedelta(seconds=11),
    )

    newly_dead = service.mark_dead_projects(db_session, dead_after_seconds=300)

    assert [p.id for p in newly_dead] == [project.id]
    assert service.get_health(db_session, project.token) is ProjectHealth.DEAD


def test_disabled_project_is_ignored_by_watchdog(service, db_session) -> None:
    project = service.create_project(db_session, "disabled", timeout_seconds=10)
    service.update_project(
        db_session,
        project.token,
        ProjectUpdateRequest(enabled=False),
    )
    service.set_last_seen(
        db_session,
        project.token,
        datetime.now(timezone.utc) - timedelta(hours=1),
    )

    assert service.mark_dead_projects(db_session, dead_after_seconds=10) == []
    assert service.get_health(db_session, project.token) is ProjectHealth.ALIVE


def test_cleanup_old_statuses_respects_project_retention(service, db_session) -> None:
    project = service.create_project(db_session, "cleanup", retention_days=1)
    old = datetime.now(timezone.utc) - timedelta(days=2)
    new = datetime.now(timezone.utc)

    service.add_status(db_session, project.token, StatusCreateRequest(message="old", timestamp=old))
    service.add_status(db_session, project.token, StatusCreateRequest(message="new", timestamp=new))

    deleted = service.cleanup_old_statuses(db_session)
    statuses = service.get_statuses(db_session, project.token)

    assert deleted == 1
    assert [status.message for status in statuses] == ["new"]


def test_retention_zero_keeps_history(service, db_session) -> None:
    project = service.create_project(db_session, "keep", retention_days=0)
    old = datetime.now(timezone.utc) - timedelta(days=100)

    service.add_status(db_session, project.token, StatusCreateRequest(message="old", timestamp=old))

    assert service.cleanup_old_statuses(db_session) == 0
    assert len(service.get_statuses(db_session, project.token)) == 1
