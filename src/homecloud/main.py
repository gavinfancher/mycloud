from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from homecloud.api.routes import router, ui_index
from homecloud.config import settings
from homecloud.state import hydrate_registry

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Homecloud Controller",
    description="Control plane for Proxmox-based instances — Tailscale MagicDNS",
    version="0.2.0",
)
app.include_router(router)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    return ui_index()


@app.on_event("startup")
def startup() -> None:
    hydrate_registry()


def cli() -> None:
    uvicorn.run(
        "homecloud.main:app",
        host=settings.controller_host,
        port=settings.controller_port,
        reload=False,
    )


if __name__ == "__main__":
    cli()
