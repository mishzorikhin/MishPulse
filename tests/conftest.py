"""Общие фикстуры для тестов MishPulse."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_project_service
from app.main import app
from app.services.project_service import ProjectService


class RecordingNotifier:
    """Заглушка Notifier, которая запоминает отправленные уведомления."""

    def __init__(self) -> None:
        self.notifications: list[tuple[str, dict[str, str]]] = []

    def notify(self, title: str, details: dict[str, str]) -> None:
        self.notifications.append((title, details))


@pytest.fixture()
def recording_notifier() -> RecordingNotifier:
    return RecordingNotifier()


@pytest.fixture()
def service(recording_notifier: RecordingNotifier) -> ProjectService:
    return ProjectService(notifier=recording_notifier)


@pytest.fixture()
def client(service: ProjectService):
    app.dependency_overrides[get_project_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
