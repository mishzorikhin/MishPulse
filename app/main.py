"""Entry point for the MishPulse FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from .api import register_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="MishPulse", version="0.1.0")
register_routes(app)


@app.on_event("startup")
async def log_startup_message() -> None:
    """Log a startup message once the application is ready."""

    logger.info("Инициализация приложения MishPulse")
