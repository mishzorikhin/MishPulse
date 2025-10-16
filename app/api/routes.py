"""API router definitions for MishPulse service."""

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/", summary="Service status message")
async def root() -> dict[str, str]:
    """Minimal placeholder endpoint until the heartbeat collector is implemented."""
    return {"message": "MishPulse backend is running"}


@router.get("/health", summary="Health check")
async def healthcheck() -> dict[str, str]:
    """Return a simple service health indicator."""
    return {"status": "ok"}
