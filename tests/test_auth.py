"""Тесты авторизации по паролю."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.config import settings


@pytest.fixture()
def secured(monkeypatch):
    """Включить проверку пароля для тестов."""

    secured_settings = replace(settings, admin_password="test-secret")
    monkeypatch.setattr("app.api.auth.settings", secured_settings)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-secret"}


def test_auth_disabled_by_default(client) -> None:
    response = client.get("/auth/status")
    assert response.status_code == 200
    assert response.json() == {"required": False, "authenticated": True}


def test_protected_routes_open_without_password(client) -> None:
    assert client.post("/projects", json={"name": "open"}).status_code == 201


def test_auth_status_when_secured(secured, client) -> None:
    assert client.get("/auth/status").json() == {"required": True, "authenticated": False}
    assert client.get("/auth/status", headers=_auth_headers()).json() == {
        "required": True,
        "authenticated": True,
    }


def test_login_endpoint(secured, client) -> None:
    assert client.post("/auth/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/auth/login", json={"password": "test-secret"}).json() == {
        "required": True,
        "authenticated": True,
    }


def test_create_project_requires_password_when_secured(secured, client) -> None:
    assert client.post("/projects", json={"name": "x"}).status_code == 401
    assert client.post("/projects", json={"name": "x"}, headers=_auth_headers()).status_code == 201


def test_heartbeat_works_without_admin_password(secured, client) -> None:
    create = client.post("/projects", json={"name": "hb"}, headers=_auth_headers())
    link = create.json()["link"]
    assert client.post(link, json={"message": "alive"}).status_code == 200


def test_summary_requires_password_when_secured(secured, client) -> None:
    assert client.get("/projects/summary").status_code == 401
    assert client.get("/projects/summary", headers=_auth_headers()).status_code == 200
