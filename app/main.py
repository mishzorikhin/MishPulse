"""Entry point for the MishPulse FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .api import register_routes
from .services import Watchdog, project_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Запустить watchdog на время жизни приложения."""

    logger.info("Инициализация приложения MishPulse")
    watchdog = Watchdog(project_service)
    watchdog.start()
    try:
        yield
    finally:
        await watchdog.stop()
        logger.info("Приложение MishPulse остановлено")


app = FastAPI(title="MishPulse", version="0.2.0", lifespan=lifespan)
register_routes(app)
