"""API package for MishPulse."""

from fastapi import FastAPI

from . import routes, ui

__all__ = ["register_routes"]


def register_routes(app: FastAPI) -> None:
    """Register all API routes on the FastAPI application."""
    app.include_router(routes.router)
    ui.register_ui(app)
