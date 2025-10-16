"""Entry point for the MishPulse FastAPI application."""

from fastapi import FastAPI

from .api import register_routes


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(title="MishPulse", version="0.1.0")
    register_routes(application)
    return application


app = create_app()
