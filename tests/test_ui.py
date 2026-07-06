"""Тесты веб-интерфейса управления."""

from __future__ import annotations


def test_ui_index_served(client) -> None:
    response = client.get("/ui")
    assert response.status_code == 200
    assert "MishPulse" in response.text
    assert "/static/js/app.js" in response.text


def test_ui_spa_fallback(client) -> None:
    response = client.get("/ui/projects/new")
    assert response.status_code == 200
    assert "id=\"app\"" in response.text


def test_static_assets_served(client) -> None:
    response = client.get("/static/css/app.css")
    assert response.status_code == 200
    assert "badge-alive" in response.text

    js = client.get("/static/js/app.js")
    assert js.status_code == 200
    assert "pageDashboard" in js.text


def test_dashboard_redirects_to_ui(client) -> None:
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/ui#/"
