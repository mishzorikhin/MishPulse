"""Entry point for the MishPulse FastAPI application."""

from fastapi import FastAPI

app = FastAPI(title="MishPulse", version="0.1.0")


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    """Return a simple service health indicator."""
    return {"status": "ok"}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """Minimal placeholder endpoint until the heartbeat collector is implemented."""
    return {"message": "MishPulse backend is running"}
