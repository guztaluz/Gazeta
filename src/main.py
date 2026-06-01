from __future__ import annotations

import logging
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src.config import get_settings


def configure_logging(level: str) -> None:
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


settings = get_settings()
configure_logging(settings.log_level)
log = structlog.get_logger()

app = FastAPI(title="Gazeta", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "driver": settings.printer_driver}


@app.get("/preview/latest")
async def preview_latest() -> FileResponse:
    latest = Path(settings.output_dir) / "latest.png"
    if not latest.exists():
        raise HTTPException(status_code=404, detail="No print yet")
    return FileResponse(latest, media_type="image/png")


# Routers
try:
    from src.routes.summary import router as summary_router
    from src.routes.raw import router as raw_router
    from src.routes.note import router as note_router

    app.include_router(summary_router)
    app.include_router(raw_router)
    app.include_router(note_router)
except ImportError:
    log.info("routes_not_yet_wired")
