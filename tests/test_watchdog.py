"""Тесты логики watchdog и переходов состояния проекта."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import ProjectHealth
from app.schemas import StatusCreateRequest


def test_silent_project_becomes_dead(service, db_session, recording_notifier) -> None:
    project = service.create_project(db_session, "silent")
    service.set_last_seen(
        db_session,
        project.token,
        datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    newly_dead = service.mark_dead_projects(db_session, dead_after_seconds=300)

    assert [p.id for p in newly_dead] == [project.id]
    assert service.get_health(db_session, project.token) is ProjectHealth.DEAD
    assert len(recording_notifier.notifications) == 1
    assert "не отвечает" in recording_notifier.notifications[0][0]


def test_fresh_project_stays_alive(service, db_session, recording_notifier) -> None:
    service.create_project(db_session, "fresh")

    assert service.mark_dead_projects(db_session, dead_after_seconds=300) == []
    assert recording_notifier.notifications == []


def test_dead_project_is_not_reported_twice(service, db_session, recording_notifier) -> None:
    project = service.create_project(db_session, "silent")
    service.set_last_seen(
        db_session,
        project.token,
        datetime.now(timezone.utc) - timedelta(hours=1),
    )

    assert len(service.mark_dead_projects(db_session, dead_after_seconds=300)) == 1
    assert service.mark_dead_projects(db_session, dead_after_seconds=300) == []
    assert len(recording_notifier.notifications) == 1


def test_heartbeat_revives_dead_project(service, db_session, recording_notifier) -> None:
    project = service.create_project(db_session, "phoenix")
    service.set_last_seen(
        db_session,
        project.token,
        datetime.now(timezone.utc) - timedelta(hours=1),
    )
    service.mark_dead_projects(db_session, dead_after_seconds=300)
    assert service.get_health(db_session, project.token) is ProjectHealth.DEAD

    service.add_status(db_session, project.token, StatusCreateRequest(message="я вернулся"))

    assert service.get_health(db_session, project.token) is ProjectHealth.ALIVE
    titles = [title for title, _ in recording_notifier.notifications]
    assert any("снова на связи" in title for title in titles)
