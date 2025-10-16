"""Entry point for the MishPulse FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from .api import register_routes


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logging.getLogger(__name__).info("Инициализация приложения MishPulse")

    application = FastAPI(title="MishPulse", version="0.1.0")
    register_routes(application)
    return application


app = create_app()
