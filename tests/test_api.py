"""Тесты HTTP API MishPulse."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _create_project(client, name: str = "demo") -> str:
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == name
    assert body["link"].startswith("/projects/")
    return body["link"]


def test_root_and_health(client) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_create_project_rejects_empty_name(client) -> None:
    response = client.post("/projects", json={"name": ""})
    assert response.status_code == 422


def test_push_and_list_statuses(client) -> None:
    link = _create_project(client)

    response = client.post(link, json={"message": "все хорошо"})
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "ok"
    assert body["message"] == "все хорошо"

    response = client.get(link)
    assert response.status_code == 200
    statuses = response.json()
    assert len(statuses) == 1
    assert statuses[0]["message"] == "все хорошо"


def test_unknown_token_returns_404(client) -> None:
    assert client.post("/projects/nope/statuses", json={"message": "x"}).status_code == 404
    assert client.get("/projects/nope/statuses").status_code == 404


def test_status_timestamp_must_increase(client) -> None:
    link = _create_project(client)
    now = datetime.now(timezone.utc)

    first = client.post(link, json={"message": "a", "timestamp": now.isoformat()})
    assert first.status_code == 200

    stale = client.post(
        link,
        json={"message": "b", "timestamp": (now - timedelta(minutes=1)).isoformat()},
    )
    assert stale.status_code == 400


def test_naive_timestamp_is_treated_as_utc(client) -> None:
    link = _create_project(client)
    naive = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)

    response = client.post(link, json={"message": "naive", "timestamp": naive.isoformat()})
    assert response.status_code == 200

    aware = datetime.now(timezone.utc) + timedelta(seconds=5)
    response = client.post(link, json={"message": "aware", "timestamp": aware.isoformat()})
    assert response.status_code == 200


def test_error_status_triggers_notification(client, recording_notifier) -> None:
    link = _create_project(client, name="worker")

    response = client.post(link, json={"level": "error", "message": "boom"})
    assert response.status_code == 200

    assert len(recording_notifier.problems) == 1
    title, details, _, _ = recording_notifier.problems[0]
    assert "worker" in title
    assert details["message"] == "boom"


def test_summary_reflects_project_health(client) -> None:
    link = _create_project(client, name="svc")
    client.post(link, json={"level": "warning", "message": "watch out"})

    response = client.get("/projects/summary")
    assert response.status_code == 200
    summary = response.json()
    assert len(summary) == 1
    assert summary[0]["name"] == "svc"
    assert summary[0]["health"] == "warning"
    assert summary[0]["last_message"] == "watch out"


def test_dashboard_renders_projects(client) -> None:
    link = _create_project(client, name="дашборд-сервис")
    client.post(link, json={"message": "пульс"})

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "дашборд-сервис" in response.text
    assert "пульс" in response.text
