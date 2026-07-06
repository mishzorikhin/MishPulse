"""Web UI static files and SPA routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def register_ui(app: FastAPI) -> None:
    """Подключить статику и одностраничный интерфейс управления."""

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/ui")
    async def ui_root() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/ui/{full_path:path}")
    async def ui_spa(full_path: str) -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_redirect() -> RedirectResponse:
        return RedirectResponse(url="/ui#/", status_code=302)
