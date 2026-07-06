"""Общие фикстуры для тестов MishPulse."""

from __future__ import annotations

import os

# До импорта приложения — тестовая БД в памяти
os.environ["MISHPULSE_DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import get_project_service
from app.db import Base, get_db
from app.main import app
from app.services.notifier import NotificationTargets
from app.services.project_service import ProjectService


class RecordingNotifier:
    """Заглушка Notifier, которая запоминает отправленные уведомления."""

    def __init__(self) -> None:
        self.problems: list[tuple[str, dict[str, str], NotificationTargets, str]] = []
        self.recoveries: list[tuple[str, dict[str, str], NotificationTargets]] = []

    def notify_problem(
        self,
        title: str,
        details: dict[str, str],
        targets: NotificationTargets,
        *,
        priority: str = "urgent",
    ) -> None:
        self.problems.append((title, details, targets, priority))

    def notify_recovery(
        self,
        title: str,
        details: dict[str, str],
        targets: NotificationTargets,
    ) -> None:
        self.recoveries.append((title, details, targets))


@pytest.fixture()
def engine():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    return test_engine


@pytest.fixture(autouse=True)
def bind_test_database(engine, monkeypatch):
    """Подменить глобальный engine/SessionLocal на тестовый."""

    test_session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr("app.db.session.engine", engine)
    monkeypatch.setattr("app.db.session.SessionLocal", test_session_factory)
    monkeypatch.setattr("app.db.SessionLocal", test_session_factory)


@pytest.fixture(autouse=True)
def clean_tables(engine):
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture()
def recording_notifier() -> RecordingNotifier:
    return RecordingNotifier()


@pytest.fixture()
def service(recording_notifier: RecordingNotifier) -> ProjectService:
    return ProjectService(notifier=recording_notifier)


@pytest.fixture()
def db_session(engine) -> Session:
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    yield session
    session.close()


@pytest.fixture()
def client(service: ProjectService, engine):
    def override_get_db():
        session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_project_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
